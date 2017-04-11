from distutils import log
from setuptools.command.build_ext import build_ext as _build_ext


class build_ext(_build_ext):

    def __init__(self, *args):
        _build_ext.__init__(self, *args)

    def has_rust_extensions(self):
        return (self.distribution.rust_extensions and
                len(self.distribution.rust_extensions) > 0)

    def check_extensions_list(self, extensions):
        if extensions:
            _build_ext.check_extensions_list(self, extensions)

    def run(self):
        """Run build_rust sub command """
        if self.has_rust_extensions():
            log.info("running build_rust")
            build_rust = self.get_finalized_command('build_rust')
            build_rust.inplace = self.inplace
            build_rust.run()

        _build_ext.run(self)
