# CFn docgen

This repo generates some useful constraints from parsing the documentation.

## Implemented properties

* `GetAtt` targets
* `Ref` values (in free text, sorry :()

## Usage

```bash
# cfn-propgen will clone the source in the background, parse and print to stdout
cfn-propgen

# use a checked-out copy of the source code
cfn-propgen -r aws-cloudformation-user-guide/doc_source

# cfn-propgen will clone the source in the background, parse and save to out.json
cfn-propgen -o out.json
```
