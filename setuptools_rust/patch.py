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
    Distribution.orig_has_ext_modules = Distribution.has_ext_modules

    def has_ext_modules(self):
        return (self.ext_modules and len(self.ext_modules) > 0 or
                self.rust_extensions and len(self.rust_extensions) > 0)

    Distribution.has_ext_modules = has_ext_modules
