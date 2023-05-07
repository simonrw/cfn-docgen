#!/usr/bin/env python

import argparse
import shutil
import tempfile
from typing import IO, Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
import json
import re
import subprocess as sp

REF_RE = re.compile(r"`Ref` returns\s*([^\\,]+)")


class ResourcePage:
    f: IO | None

    def __init__(self, path: Path):
        self.path = path
        self.f = None

    def __enter__(self):
        self.f = open(self.path)
        return self

    def __exit__(self, tb_, *args):
        # TODO: handle exception
        if self.f is not None:
            self.f.close()

    def resource_name(self) -> str:
        assert self.f is not None

        self.f.seek(0)
        # read header
        line = self.f.readline()
        resource_name = line.split("#")[1].strip().split("<")[0].strip()
        return resource_name

    def getatt_targets(self) -> Generator[str, None, None]:
        for line in self._lines():
            if "-fn::getatt" not in line:
                continue

            yield line.split()[0].strip().replace("`", "")

    def ref(self) -> str | None:
        candidates = []
        tracking = False
        for line in self._lines():
            if line.startswith("### Ref"):
                tracking = True
            elif line.startswith("### Fn::GetAtt"):
                tracking = False

            if (
                tracking
                and "logical ID of this resource to the intrinsic `Ref` function"
                in line
            ):
                match = REF_RE.search(line)
                if not match:
                    continue

                candidates.append(match.group(1))

        if len(candidates) == 0:
            return None
        elif len(candidates) > 1:
            raise RuntimeError(
                f"too many ref target candidates for {self.resource_name()}: {candidates}"
            )

        return candidates[0]

    def _lines(self) -> Generator[str, None, None]:
        assert self.f is not None
        self.f.seek(0)
        for line in self.f:
            line = line.strip()
            if not line:
                continue

            yield line


def list_files(root: Path) -> Generator[Path, None, None]:
    assert root.is_dir()
    contents = root.glob("aws-resource-*.md")
    yield from contents

    # special case for s3
    yield root.joinpath("aws-properties-s3-bucket.md")


class LocalSource:
    def __init__(self, root: Path):
        self.root = root

    def files(self) -> Generator[Path, None, None]:
        return list_files(self.root)


class RemoteSource:
    def files(self) -> Generator[Path, None, None]:
        with self._temppath() as tdir:
            self._clone_repo(tdir)
            yield from list_files(tdir.joinpath("doc_source"))

    def _clone_repo(self, root: Path):
        cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/awsdocs/aws-cloudformation-user-guide",
            str(root),
        ]
        child = sp.run(cmd, capture_output=True, encoding="utf8")
        if child.returncode != 0:
            raise RuntimeError(f"cloning source: {child.stderr}")

    @contextmanager
    def _temppath(self) -> Iterator[Path]:
        tdir = tempfile.mkdtemp()
        try:
            yield Path(tdir)
        finally:
            shutil.rmtree(tdir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--root", type=Path, required=False)
    parser.add_argument(
        "-o", "--output", required=False, default="-", type=argparse.FileType("w")
    )
    args = parser.parse_args()

    if args.root:
        source = LocalSource(args.root)
    else:
        source = RemoteSource()

    resources = {}
    for file in source.files():
        with ResourcePage(file) as page:
            resources[page.resource_name()] = {
                "targets": list(page.getatt_targets()),
                "ref": page.ref(),
            }

    json.dump(resources, args.output, indent=2)


if __name__ == "__main__":
    main()
