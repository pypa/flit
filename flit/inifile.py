import configparser
from . import common

class ConfigError(ValueError):
    pass

metadata_list_fields = {
    'classifiers',
    'requires',
}

metadata_allowed_fields = {
    'module',
    'author',
    'author-email',
    'maintainer',
    'maintainer-email',
    'home-page',
    'license',
    'keywords',
    'requires-python'
} | metadata_list_fields

metadata_required_fields = {
    'module',
    'author',
    'author-email',
    'home-page',
}

def read_pkg_ini(path):
    """Read and check the -pkg.ini file with data about the package.
    """
    cp = configparser.ConfigParser()
    with path.open() as f:
        cp.read_file(f)

    unknown_sections = set(cp.sections()) - {'metadata', 'scripts'}
    if unknown_sections:
        raise ConfigError('Unknown sections: ' + ', '.join(unknown_sections))

    if not cp.has_section('metadata'):
        raise ConfigError('[metadata] section is required')

    md_sect = cp['metadata']
    if not set(md_sect).issuperset(metadata_required_fields):
        missing = metadata_required_fields - set(md_sect)
        raise ConfigError("Required fields missing: " + '\n'.join(missing))

    module = md_sect.pop('module')
    if not module.isidentifier():
        raise ConfigError("Module name %r is not a valid identifier" % module)

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

    # What we call requires in the ini file is technically requires_dist in
    # the metadata.
    if 'requires' in md_dict:
        md_dict['requires_dist'] = md_dict.pop('requires')

    if cp.has_section('scripts'):
        scripts_dict = {k: common.parse_entry_point(v) for k, v in cp['scripts'].items()}
    else:
        scripts_dict = {}

    return {
        'module': module,
        'metadata': md_dict,
        'scripts': scripts_dict,
    }
