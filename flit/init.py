import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import tomli_w


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
        with (get_data_dir() / 'init_defaults.json').open(encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def store_defaults(d):
    data_dir = get_data_dir()
    try:
        data_dir.mkdir(parents=True)
    except FileExistsError:
        pass
    with (data_dir / 'init_defaults.json').open('w', encoding='utf-8') as f:
        json.dump(d, f, indent=2)

license_choices = [
    ('mit', "MIT - simple and permissive"),
    ('apache', "Apache - explicitly grants patent rights"),
    ('gpl3', "GPL - ensures that code based on this is shared with the same terms"),
    ('skip', "Skip - choose a license later"),
]

license_names_to_spdx = {
    'mit': 'MIT',
    'apache': 'Apache-2.0',
    'gpl3': 'GPL-3.0-or-later',
}

license_templates_dir = Path(__file__).parent / 'license_templates'

class IniterBase:
    def __init__(self, directory='.'):
        self.directory = Path(directory)
        self.defaults = get_defaults()

    def validate_email(self, s):
        # Properly validating an email address is much more complex
        return bool(re.match(r'.+@.+', s)) or s == ""

    def validate_homepage(self, s):
        return not s or s.startswith(('http://', 'https://'))

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

        src_dir = self.directory / 'src'
        if src_dir.is_dir():
            for p in src_dir.iterdir():
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
        license_text = (license_templates_dir / name).read_text('utf-8')

        (self.directory / 'LICENSE').write_text(
            license_text.format(year=year, author=author), encoding='utf-8'
        )

    def find_readme(self):
        allowed = ("readme.md","readme.rst","readme.txt")
        for fl in self.directory.glob("*.*"):
            if fl.name.lower() in allowed:
                return fl.name
        return None


class TerminalIniter(IniterBase):
    def prompt_text(self, prompt, default, validator, retry_msg="Try again."):
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

            print(retry_msg)

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
        if (self.directory / 'pyproject.toml').exists():
            resp = input("pyproject.toml exists - overwrite it? [y/N]: ")
            if (not resp) or resp[0].lower() != 'y':
                return

        module = self.prompt_text('Module name', self.guess_module_name(),
                                  str.isidentifier)
        author = self.prompt_text('Author', self.defaults.get('author'),
                                  lambda s: True)
        author_email = self.prompt_text('Author email',
                        self.defaults.get('author_email'), self.validate_email)
        if 'home_page_template' in self.defaults:
            home_page_default = self.defaults['home_page_template'].replace(
                                                        '{modulename}', module)
        else:
            home_page_default = None
        home_page = self.prompt_text('Home page', home_page_default, self.validate_homepage,
                                     retry_msg="Should start with http:// or https:// - try again.")
        license = self.prompt_options('Choose a license (see http://choosealicense.com/ for more info)',
                    license_choices, self.defaults.get('license'))

        readme = self.find_readme()

        self.update_defaults(author=author, author_email=author_email,
                             home_page=home_page, module=module, license=license)

        # Format information as TOML
        # This is ugly code, but I want the generated pyproject.toml, which
        # will mostly be edited by hand, to look a particular way - e.g. authors
        # in inline tables. It's easier to 'cheat' with some string formatting
        # than to do this through a TOML library.
        author_info = []
        if author:
            author_info.append(f'name = {json.dumps(author, ensure_ascii=False)}')
        if author_email:
            author_info.append(f'email = {json.dumps(author_email)}')
        if author_info:
            authors_list = "[{%s}]" % ", ".join(author_info)
        else:
            authors_list = "[]"

        if license != 'skip':
            self.write_license(license, author)

        with (self.directory / 'pyproject.toml').open('w', encoding='utf-8') as f:
            f.write(TEMPLATE.format(
                name=json.dumps(module), authors=authors_list
            ))
            if readme:
                f.write(tomli_w.dumps({'readme': readme}))
            if license != 'skip':
                f.write(tomli_w.dumps({'license': license_names_to_spdx[license]}))
                f.write(f"license-files = {json.dumps(['LICENSE'])}\n")
            f.write('dynamic = ["version", "description"]\n')
            if home_page:
                f.write("\n" + tomli_w.dumps({
                    'project': {'urls': {'Home': home_page}}
                }))

        print()
        print("Written pyproject.toml; edit that file to add optional extra info.")

TEMPLATE = """\
[build-system]
requires = ["flit_core >=3.11,<4"]
build-backend = "flit_core.buildapi"

[project]
name = {name}
authors = {authors}
"""

if __name__ == '__main__':
    TerminalIniter().initialise()
