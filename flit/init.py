import configparser
from datetime import date
import json
import os
from pathlib import Path
import re
import sys

def get_data_dir():
    """Get the directory path for flit user data files.
    """
    home = os.path.realpath(os.path.expanduser('~'))

    if sys.platform == 'darwin':
        d = Path(home, 'Library')
    elif os.name == 'nt':
        appdata = os.environ.get('APPDATA', None)
        if appdata:
            d = Path(appdata)
        else:
            d = Path(home, 'AppData', 'Roaming')
    else:
        # Linux, non-OS X Unix, AIX, etc.
        xdg = os.environ.get("XDG_DATA_HOME", None)
        d = Path(xdg) if xdg else Path(home, '.local/share')

    return d / 'flit'

def get_defaults():
    try:
        with (get_data_dir() / 'init_defaults.json').open() as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def store_defaults(d):
    data_dir = get_data_dir()
    try:
        data_dir.mkdir(parents=True)
    except FileExistsError:
        pass
    with (data_dir / 'init_defaults.json').open('w') as f:
        json.dump(d, f, indent=2)

license_choices = [
    ('mit', "MIT - simple and permissive"),
    ('apache', "Apache - explicitly grants patent rights"),
    ('gpl3', "GPL - ensures that code based on this is shared with the same terms"),
    ('skip', "Skip - choose a license later"),
]

license_names_to_classifiers = {
    'mit': 'License :: OSI Approved :: MIT License',
    'gpl3': 'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'apache': 'License :: OSI Approved :: Apache Software License'
}

license_templates_dir = Path(__file__).parent / 'license_templates'

class IniterBase:
    def __init__(self, directory='.'):
        self.directory = Path(directory)
        self.defaults = get_defaults()

    def validate_email(self, s):
        # Properly validating an email address is much more complex
        return bool(re.match(r'.+@.+', s))

    def guess_module_name(self):
        packages, modules = [], []
        for p in self.directory.iterdir():
            if not p.stem.isidentifier():
                continue

            if p.is_dir() and (p / '__init__.py').is_file():
                if p.name not in {'test', 'tests'}:
                    packages.append(p.name)

            elif p.is_file() and p.suffix == '.py':
                if p.stem not in {'setup'} and not p.name.startswith('test_'):
                    modules.append(p.stem)

        if len(packages) == 1:
            return packages[0]
        elif len(packages) == 0 and len(modules) == 1:
            return modules[0]
        else:
            return None
    
    def update_defaults(self, author, author_email, module, home_page, license):
        new_defaults = {'author': author, 'author_email': author_email,
                        'license': license}
        name_chunk_pat = r'\b{}\b'.format(re.escape(module))
        if re.search(name_chunk_pat, home_page):
            new_defaults['home_page_template'] = \
                re.sub(name_chunk_pat, '{modulename}', home_page, flags=re.I)
        if any(new_defaults[k] != self.defaults.get(k) for k in new_defaults):
            self.defaults.update(new_defaults)
            store_defaults(self.defaults)

    def write_license(self, name, author):
        if (self.directory / 'LICENSE').exists():
            return
        year = date.today().year
        with (license_templates_dir / name).open() as f:
            license_text = f.read()

        with (self.directory / 'LICENSE').open('w') as f:
            f.write(license_text.format(year=year, author=author))


class TerminalIniter(IniterBase):
    def prompt_text(self, prompt, default, validator):
        if default is not None:
            p = "{} [{}]: ".format(prompt, default)
        else:
            p = prompt + ': '
        while True:
            response = input(p)
            if response == '' and default is not None:
                response = default
            if validator(response):
                return response

            print("Try again.")

    def prompt_options(self, prompt, options, default=None):
        default_ix = None

        print(prompt)
        for i, (key, text) in enumerate(options, start=1):
            print("{}. {}".format(i, text))
            if key == default:
                default_ix = i

        while True:
            p = "Enter 1-" + str(len(options))
            if default_ix is not None:
                p += ' [{}]'.format(default_ix)
            response = input(p+': ')
            if (default_ix is not None) and response == '':
                return default

            if response.isnumeric():
                ir = int(response)
                if 1 <= ir <= len(options):
                    return options[ir-1][0]
            print("Try again.")

    def initialise(self):
        if (self.directory / 'flit.ini').exists():
            resp = input("flit.ini exists - overwrite it? [y/N]: ")
            if (not resp) or resp[0].lower() != 'y':
                return

        module = self.prompt_text('Module name', self.guess_module_name(),
                                  str.isidentifier)
        author = self.prompt_text('Author', self.defaults.get('author'),
                                  lambda s: s != '')
        author_email = self.prompt_text('Author email',
                        self.defaults.get('author_email'), self.validate_email)
        if 'home_page_template' in self.defaults:
            home_page_default = self.defaults['home_page_template'].replace(
                                                        '{modulename}', module)
        else:
            home_page_default = None
        home_page = self.prompt_text('Home page', home_page_default,
                                     lambda s: s != '')
        license = self.prompt_options('Choose a license',
                    license_choices, self.defaults.get('license'))

        self.update_defaults(author=author, author_email=author_email,
                             home_page=home_page, module=module, license=license)

        cp = configparser.ConfigParser()
        cp['metadata'] = {}
        cp['metadata'].update([
            ('module', module),
            ('author', author),
            ('author-email', author_email),
            ('home-page', home_page),
        ])
        if license != 'skip':
            cp['metadata']['classifiers'] = license_names_to_classifiers[license]
            self.write_license(license, author)
        with (self.directory / 'flit.ini').open('w') as f:
            cp.write(f)
        print()
        print("Written flit.ini; edit that file to add optional extra info.")

if __name__ == '__main__':
    TerminalIniter().initialise()
