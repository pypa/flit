#!/bin/bash
# Update the vendored copy of packaging
set -euo pipefail

version=$1
echo "Bundling packaging version $version"

rm -rf flit_core/vendor/packaging*
pip install --target flit_core/vendor/ --no-compile "packaging==$version"

# Delete some files that aren't useful in this context.
# Only keep __init__.py and licenses package
python -c "$(cat <<- EOF
import os
dir = "flit_core/vendor/packaging"
files = [f for f in os.listdir(dir) if f not in ('__init__.py', 'licenses')]
for file in files:
  os.remove(dir + os.sep + file)
EOF
)"

# Leave LICENSE & METADATA present.
rm flit_core/vendor/packaging*.dist-info/{INSTALLER,RECORD,REQUESTED,WHEEL}

for file in flit_core/vendor/packaging/licenses/*.py; do
  # Convert absolute imports to relative (from packaging.licenses.foo -> from .foo)
  sed -i -E 's/((from|import)[[:space:]]+)packaging\.licenses\./\1\./' "$file"
done
