# coding: utf-8
from __future__ import unicode_literals

import glob
import os
import string

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import setuptools

from distutils import log
from distutils.command.build import build

from .extension import RustExtension


__all__ = ["tomlgen"]


class tomlgen_rust(setuptools.Command):

    user_options = [

    ]

    def initialize_options(self):

        self.dependencies = None
        self.authors = None
        self.create_workspace = False

        # command to find build directories
        self.build = build(self.distribution)

        # parse config files
        self.cfg = configparser.ConfigParser()
        self.cfg.read(self.distribution.find_config_files())

    def finalize_options(self):

        # Finalize previous commands
        self.distribution.finalize_options()
        self.build.ensure_finalized()

        # Shortcuts
        self.extensions = self.distribution.rust_extensions
        self.workspace = os.path.dirname(self.distribution.script_name)

        # Build list of authors
        if self.authors is not None:
            self.authors = "[{}]".format(
                ", ".join(author.strip() for author in self.authors.split('\n')))
        else:
            self.authors = '["{} <{}>"]'.format(
                self.distribution.get_author(),
                self.distribution.get_author_email())

    def run(self):
        for ext in self.extensions:
            log.info("creating 'Cargo.toml' for '%s'", ext.name)
            toml = self.build_cargo_toml(ext)
            with open(ext.path, 'w') as manifest:
                toml.write(manifest)

        if self.create_workspace and self.extensions:
            log.info("creating 'Cargo.toml' for workspace")
            toml = self.build_workspace_toml()
            with open(os.path.join(self.workspace, "Cargo.toml"), 'w') as manifest:
                toml.write(manifest)

    def build_cargo_toml(self, ext):

        quote = '"{}"'.format
        dist = self.distribution
        toml = configparser.ConfigParser()

        toml.add_section("package")
        toml.set("package", "name", quote(ext.name))
        toml.set("package", "version", quote(dist.get_version()))
        toml.set("package", "authors", self.authors)
        toml.set("package", "publish", "false")

        if self.create_workspace:
            toml.set("package", "workspace", quote(os.path.abspath(self.workspace)))

        toml.add_section("lib")
        toml.set("lib", "crate-type", '["cdylib"]')
        toml.set("lib", "name", quote(ext.basename))
        toml.set("lib", "path", quote(ext.libfile))

        toml.add_section("dependencies")
        for dep, options in self.iter_dependencies(ext):
            toml.set("dependencies", dep, options)

        return toml

    def build_workspace_toml(self):

        members = [os.path.dirname(os.path.relpath(ext.path)) for ext in self.extensions]
        members = ['"{}"'.format(m) for m in members]

        toml = configparser.ConfigParser()
        toml.add_section('workspace')
        toml.set('workspace', 'members', '[{}]'.format(', '.join(members)))

        return toml

    def iter_dependencies(self, ext=None):

        command = self.get_command_name()
        sections = ['{}.dependencies'.format(command)]

        if ext is not None:
            sections.append('{}.dependencies.{}'.format(command, ext.name))

        for section in sections:
            if self.cfg.has_section(section):
                for dep, options in self.cfg.items(section):
                    yield dep, options



def _slugify(name):
    allowed = set(string.ascii_letters + string.digits + '_')
    slug = [char if char in allowed else '_' for char in name]
    return ''.join(slug)

def find_rust_extensions(*directories, libfile="lib.rs", **kwargs):

    directories = directories or [os.getcwd()]
    extensions = []

    for directory in directories:
        for base, dirs, files in os.walk(directory):
            if libfile in files:
                dotpath = os.path.relpath(base).replace(os.path.sep, '.')
                tomlpath = os.path.join(base, "Cargo.toml")
                ext = RustExtension(dotpath, tomlpath, **kwargs)
                ext.libfile = os.path.join(base, libfile)
                ext.basename = os.path.basename(base)
                extensions.append(ext)

    return extensions
