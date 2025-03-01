# Call with path to SPDX license-list-data repo, cloned from:
#   https://github.com/spdx/license-list-data

import json
import pprint
import sys
from pathlib import Path

list_data_repo = Path(sys.argv[1])
with (list_data_repo / 'json' / 'licenses.json').open('rb') as f:
    licenses_json = json.load(f)

condensed = {
    l['licenseId'].lower(): {'id': l['licenseId']}
    for l in licenses_json['licenses']
    if not l['isDeprecatedLicenseId']
}

with Path('flit_core', 'flit_core', '_spdx_data.py').open('w') as f:
    f.write("# This file is generated from SPDX license data; don't edit it manually.\n\n")

    f.write("licenses = \\\n")
    pprint.pprint(condensed, f)
