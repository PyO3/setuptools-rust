# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# -- Project information -----------------------------------------------------

project = "setuptools-rust"
copyright = "2021, The PyO3 Contributors"
author = "The PyO3 Contributors"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_theme_options = {}

# -- Custom HTML link transformation to make documentation links relative --

# This is necessary because the README.md (for example) has links to the latest
# documentation, but we want them to be relative to the specific docs version.

from sphinx.transforms import SphinxTransform

DOCS_URL = "https://setuptools-rust.readthedocs.io/en/latest/"


class RelativeDocLinks(SphinxTransform):

    default_priority = 750

    def apply(self):
        from docutils.nodes import Text, reference

        baseref = lambda o: (
            isinstance(o, reference) and o.get("refuri", "").startswith(DOCS_URL)
        )
        basetext = lambda o: (isinstance(o, Text) and o.startswith(DOCS_URL))
        for node in self.document.traverse(baseref):
            target = node["refuri"].replace(DOCS_URL, "", 1)
            node.replace_attr("refuri", target)
            for t in node.traverse(basetext):
                t1 = Text(t.replace(DOCS_URL, "", 1), t.rawsource)
                t.parent.replace(t, t1)
        return


# end of class


def setup(app):
    app.add_transform(RelativeDocLinks)
    return
