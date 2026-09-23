"""Configuração do Sphinx para a documentação do Clima Pipeline."""

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
project = "Clima Pipeline"
copyright = "2026, Clima Pipeline"
author = "Clima Pipeline"

try:
    from clima_pipeline import __version__ as release
except ImportError:
    release = "0.1.0"
version = release

# -- General configuration ----------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",       # extrai docstrings de classes/funções automaticamente
    "sphinx.ext.napoleon",      # entende docstrings em estilo Google/NumPy, além de prosa livre
    "sphinx.ext.viewcode",      # adiciona link "[source]" para o código-fonte
    "sphinx.ext.intersphinx",   # permite linkar para a doc oficial do Python/pandas/etc.
    "sphinx.ext.autosummary",   # gera tabelas-resumo de módulos/classes/funções
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

language = "pt_BR"

autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"

napoleon_google_docstring = True
napoleon_numpy_docstring = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20", None),
}

# -- Options for HTML output --------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
