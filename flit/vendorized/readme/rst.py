# Copyright 2014 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Copied from https://github.com/pypa/readme_renderer
# Commit 5b455a9c5bafc1732dafad9619bcbfa8e15432c9

from __future__ import absolute_import, division, print_function

import io
import os.path

from docutils.core import publish_parts
from docutils.writers.html4css1 import HTMLTranslator, Writer
from docutils.utils import SystemMessage

from .clean import clean


class ReadMeHTMLTranslator(HTMLTranslator):

    def depart_image(self, node):
        uri = node["uri"]
        ext = os.path.splitext(uri)[1].lower()
        # we need to swap RST's use of `object` with `img` tags
        # see http://git.io/5me3dA
        if ext == ".svg":
            # preserve essential attributes
            atts = {}
            for attribute, value in node.attributes.items():
                # we have no time for empty values
                if value:
                    if attribute == "uri":
                        atts["src"] = value
                    else:
                        atts[attribute] = value

            # toss off `object` tag
            self.body.pop()
            # add on `img` with attributes
            self.body.append(self.starttag(node, "img", **atts))


SETTINGS = {
    # Cloaking email addresses provides a small amount of additional
    # privacy protection for email addresses inside of a chunk of ReST.
    "cloak_email_addresses": True,

    # Prevent a lone top level heading from being promoted to document
    # title, and thus second level headings from being promoted to top
    # level.
    "doctitle_xform": True,

    # Prevent a lone subsection heading from being promoted to section
    # title, and thus second level headings from being promoted to top
    # level.
    "sectsubtitle_xform": True,

    # Set our initial header level
    "initial_header_level": 2,

    # Prevent local files from being included into the rendered output.
    # This is a security concern because people can insert files
    # that are part of the system, such as /etc/passwd.
    "file_insertion_enabled": False,

    # Halt rendering and throw an exception if there was any errors or
    # warnings from docutils.
    "halt_level": 2,

    # Output math blocks as LaTeX that can be interpreted by MathJax for
    # a prettier display of Math formulas.
    "math_output": "MathJax",

    # Disable raw html as enabling it is a security risk, we do not want
    # people to be able to include any old HTML in the final output.
    "raw_enabled": False,

    # Disable all system messages from being reported.
    "report_level": 5,

    # Use typographic quotes, and transform --, ---, and ... into their
    # typographic counterparts.
    "smart_quotes": True,

    # Strip all comments from the rendered output.
    "strip_comments": True,

    # PATCH FOR FLIT ----------------------------------
    # Disable syntax highlighting so we don't need Pygments installed.
    "syntax_highlight": "none",
    # -------------------------------------------------
}


def render(raw, stream=None):
    if stream is None:
        # Use a io.StringIO as the warning stream to prevent warnings from
        # being printed to sys.stderr.
        stream = io.StringIO()

    settings = SETTINGS.copy()
    settings["warning_stream"] = stream

    writer = Writer()
    writer.translator_class = ReadMeHTMLTranslator

    try:
        parts = publish_parts(raw, writer=writer, settings_overrides=settings)
    except SystemMessage:
        rendered = None
    else:
        rendered = parts.get("fragment")

    if rendered:
        return clean(rendered)
    else:
        return None
