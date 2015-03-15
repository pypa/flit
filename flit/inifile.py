import configparser
from . import common

class ConfigError(ValueError):
    pass

metadata_list_fields = {
    'classifiers',
    'requires',
}

metadata_allowed_fields = {
    'author',
    'author-email',
    'maintainer',
    'maintainer-email',
    'home-page',
    'license',
    'keywords',
    'requires-python'
} | metadata_list_fields

def read_pypi_ini(path):
    cp = configparser.ConfigParser()
    with path.open() as f:
        cp.read_file(f)

    unknown_sections = set(cp.sections()) - {'metadata', 'scripts'}
    if unknown_sections:
        raise ConfigError('Unknown sections: ' + ', '.join(unknown_sections))

    if not cp.has_section('metadata'):
        raise ConfigError('[metadata] section is required')

    md_sect = cp['metadata']
    if 'author-email' not in md_sect:
        raise ConfigError('author-email key is required')

    md_dict = {}

    if 'description-file' in md_sect:
        description_file = path.parent / md_sect.pop('description-file')
        with description_file.open() as f:
            md_dict['description'] = f.read()

    for key, value in md_sect.items():
        if key not in metadata_allowed_fields:
            raise ConfigError("Unrecognised metadata key:", key)

        k2 = key.replace('-', '_')
        if key in metadata_list_fields:
            md_dict[k2] = value.splitlines()
        else:
            md_dict[k2] = value

    if cp.has_section('scripts'):
        scripts_dict = {k: common.parse_entry_point(v) for k, v in cp['scripts'].items()}
    else:
        scripts_dict = {}

    return {
        'metadata': md_dict,
        'scripts': scripts_dict,
    }
