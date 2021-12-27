#!/bin/bash
# Update the vendored copy of tomli
set -euo pipefail

version=$1
echo "Bundling tomli version $version"

rm -rf flit_core/vendor/tomli*
pip install --target flit_core/vendor/ "tomli==$version"

# Convert absolute imports to relative (from tomli.foo -> from .foo)
for file in flit_core/vendor/tomli/*.py; do
  sed -i -E 's/((from|import)[[:space:]]+)tomli\./\1\./' "$file"
done

# Delete some files that aren't useful in this context.
# Leave LICENSE & METADATA present.
rm flit_core/vendor/tomli*.dist-info/{INSTALLER,RECORD,REQUESTED,WHEEL}
