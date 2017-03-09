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


# monkey patch "sdist_add_defaults"

def _add_defaults_ext(self):
    if (self.distribution.ext_modules and
            len(self.distribution.ext_modules) > 0):
        build_ext = self.get_finalized_command('build_ext')
        self.filelist.extend(build_ext.get_source_files())


if has_py36compat:
    sdist_add_defaults._add_defaults_ext = _add_defaults_ext
