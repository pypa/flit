import configparser
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

license_names_to_classifiers = {
    'BSD': 'License :: OSI Approved :: BSD License',
    'GPL': 'License :: OSI Approved :: GPL License',
    'Apache': 'License :: OSI Approved :: Apache License'
}

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

    def prompt_options(self, prompt, options, default_ix=None, allow_other=False,
                       validator=None):
        if (default_ix is not None) and not (0 <= default_ix < len(options)):
            default_ix = None

        print(prompt)
        for i, opt in enumerate(options, start=1):
            print("{}. {}".format(i, opt))
        if allow_other:
            print("0. Other")
        while True:
            p = "Enter 1-" + str(len(options))
            if allow_other:
                p += ' or 0'
            if default_ix is not None:
                p += ' [{}]'.format(default_ix+1)
            response = input(p+': ')
            if (default_ix is not None) and response == '':
                return options[default_ix]

            if response.isnumeric():
                ir = int(response)
                if 1 <= ir <= len(options):
                    return options[ir-1]
                elif allow_other and (ir == 0):
                    other = input("Other: ")
                    if validator is None or validator(other):
                        return other
            print("Try again.")

    def initialise(self):
        if (self.directory / 'flit.ini').exists():
            resp = input("flit.ini exists - overwrite it? [y/N]: ")
            if resp[0].lower() != 'y':
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
        license_choices = ['BSD', 'GPL', 'Apache', 'Skip']
        try:
            default_license_ix = license_choices.index(self.defaults.get('license'))
        except ValueError:
            default_license_ix = None
        license = self.prompt_options('Choose a license',
                    license_choices, default_license_ix)

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
        if license != 'Skip':
            cp['metadata']['classifiers'] = license_names_to_classifiers[license]
        with (self.directory / 'flit.ini').open('w') as f:
            cp.write(f)
        print()
        print("Written flit.ini; edit that file to add optional extra info.")

if __name__ == '__main__':
    TerminalIniter().initialise()
