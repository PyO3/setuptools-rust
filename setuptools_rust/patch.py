from distutils.dist import Distribution
from distutils.command.build import build as Build
from setuptools.command import develop

try:
    from setuptools.command.py36compat import sdist_add_defaults
    has_py36compat = True
except ImportError:
    has_py36compat = False


# allow to use 'rust_extensions' parameter for setup() call
Distribution.rust_extensions = ()


orig_has_ext_modules = Distribution.has_ext_modules

def has_ext_modules(self):
    return (self.ext_modules and len(self.ext_modules) > 0 or
            self.rust_extensions and len(self.rust_extensions) > 0)


Distribution.has_ext_modules = has_ext_modules


# add support for build_rust sub-command
def has_rust_extensions(self):
    return (self.distribution.rust_extensions and
            len(self.distribution.rust_extensions) > 0)


Build.has_rust_extensions = has_rust_extensions
Build.sub_commands.append(('build_rust', Build.has_rust_extensions))

# monkey patch "develop" command
orig_run_command = develop.develop.run_command


def monkey_run_command(self, cmd):
    orig_run_command(self, cmd)

    if cmd == 'build_ext':
        self.reinitialize_command('build_rust', inplace=1)
        orig_run_command(self, 'build_rust')


develop.develop.run_command = monkey_run_command


if has_py36compat:
    # monkey patch "sdist_add_defaults"

    def _add_defaults_ext(self):
        if (self.distribution.ext_modules and
                len(self.distribution.ext_modules) > 0):
            build_ext = self.get_finalized_command('build_ext')
            self.filelist.extend(build_ext.get_source_files())

    sdist_add_defaults._add_defaults_ext = _add_defaults_ext
else:
    from distutils.command.build_ext import build_ext
    from setuptools.command.bdist_egg import bdist_egg

    orig_get_source_files = build_ext.get_source_files

    def get_source_files(self):
        if self.extensions:
            return orig_get_source_files(self)
        else:
            return []

    build_ext.get_source_files = get_source_files

    orig_get_ext_outputs = bdist_egg.get_ext_outputs

    def get_ext_outputs(self):
        Distribution.has_ext_modules = orig_has_ext_modules
        try:
            return orig_get_ext_outputs(self)
        finally:
            Distribution.has_ext_modules = has_ext_modules


    bdist_egg.get_ext_outputs = get_ext_outputs

    orig_run = bdist_egg.run

    def run(self):
        self.run_command("build_rust")
        orig_run(self)

    bdist_egg.run = run
