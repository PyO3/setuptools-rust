from distutils.command.clean import clean
from distutils.command.check import check
from distutils.command.install import install
from distutils.dist import Distribution as DistDistribution
from setuptools.dist import Distribution


def monkey_patch_dist(build_ext):
    # allow to use 'rust_extensions' parameter for setup() call
    Distribution.rust_extensions = ()

    # replace setuptools build_ext
    Distribution.orig_get_command_class = Distribution.get_command_class

    def get_command_class(self, command):
        if command == 'build_ext':
            if command not in self.cmdclass:
                self.cmdclass[command] = build_ext

        return self.orig_get_command_class(command)

    Distribution.get_command_class = get_command_class

    # use custom has_ext_modules
    DistDistribution.orig_has_ext_modules = DistDistribution.has_ext_modules

    def has_ext_modules(self):
        return (self.ext_modules and len(self.ext_modules) > 0 or
                self.rust_extensions and len(self.rust_extensions) > 0)

    DistDistribution.has_ext_modules = has_ext_modules

    # this is required because, install directly access distribution's
    # ext_modules attr to check if dist has ext modules
    install.orig_finalize_options = install.finalize_options

    def finalize_options(self):
        ext_modules = self.distribution.ext_modules

        # all ext modules
        mods = []
        if self.distribution.ext_modules:
            mods.extend(self.distribution.ext_modules)
        if self.distribution.rust_extensions:
            mods.extend(self.distribution.rust_extensions)

        self.distribution.ext_modules = mods

        self.orig_finalize_options()

        # restore ext_modules
        self.distribution.ext_modules = ext_modules

    install.finalize_options = finalize_options

    # clean rust project
    def run_clean(self):
        self.orig_run()

        if not self.dry_run:
            self.run_command("clean_rust")

    clean.orig_run = clean.run
    clean.run = run_clean

    # check rust project
    def run_check(self):
        self.orig_run()
        self.run_command("check_rust")

    check.orig_run = check.run
    check.run = run_check
