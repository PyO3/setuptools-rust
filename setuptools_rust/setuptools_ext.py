from distutils import log
from distutils.command.check import check
from distutils.command.clean import clean
from setuptools.command.install import install
from setuptools.command.build_ext import build_ext

try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    bdist_wheel = None


def add_rust_extension(dist):
    build_ext_base_class = dist.cmdclass.get('build_ext', build_ext)

    class build_ext_rust_extension(build_ext_base_class):
        def run(self):
            if self.distribution.rust_extensions:
                log.info("running build_rust")
                build_rust = self.get_finalized_command("build_rust")
                build_rust.inplace = self.inplace
                build_rust.plat_name = self.plat_name
                build_rust.run()

            build_ext_base_class.run(self)
    dist.cmdclass['build_ext'] = build_ext_rust_extension

    clean_base_class = dist.cmdclass.get('clean', clean)

    class clean_rust_extension(clean_base_class):
        def run(self):
            clean_base_class.run(self)
            if not self.dry_run:
                self.run_command("clean_rust")
    dist.cmdclass['clean'] = clean_rust_extension

    check_base_class = dist.cmdclass.get('check', check)

    class check_rust_extension(check_base_class):
        def run(self):
            check_base_class.run(self)
            self.run_command("check_rust")
    dist.cmdclass["check"] = check_rust_extension

    install_base_class = dist.cmdclass.get('install', install)

    # this is required because, install directly access distribution's
    # ext_modules attr to check if dist has ext modules
    class install_rust_extension(install_base_class):
        def finalize_options(self):
            ext_modules = self.distribution.ext_modules

            # all ext modules
            mods = []
            if self.distribution.ext_modules:
                mods.extend(self.distribution.ext_modules)
            if self.distribution.rust_extensions:
                mods.extend(self.distribution.rust_extensions)

                scripts = []
                for ext in self.distribution.rust_extensions:
                    scripts.extend(ext.entry_points())

                if scripts:
                    if not self.distribution.entry_points:
                        self.distribution.entry_points = {"console_scripts": scripts}
                    else:
                        ep_scripts = self.distribution.entry_points.get("console_scripts")
                        if ep_scripts:
                            for script in scripts:
                                if script not in ep_scripts:
                                    ep_scripts.append(scripts)
                        else:
                            ep_scripts = scripts

                        self.distribution.entry_points["console_scripts"] = ep_scripts

            self.distribution.ext_modules = mods

            install_base_class.finalize_options(self)

            # restore ext_modules
            self.distribution.ext_modules = ext_modules
    dist.cmdclass["install"] = install_rust_extension

    if bdist_wheel is not None:
        bdist_wheel_base_class = dist.cmdclass.get("bdist_wheel", bdist_wheel)

        # this is for console entries
        class bdist_wheel_rust_extension(bdist_wheel_base_class):
            def finalize_options(self):
                scripts = []
                for ext in self.distribution.rust_extensions:
                    scripts.extend(ext.entry_points())

                if scripts:
                    if not self.distribution.entry_points:
                        self.distribution.entry_points = {"console_scripts": scripts}
                    else:
                        ep_scripts = self.distribution.entry_points.get("console_scripts")
                        if ep_scripts:
                            for script in scripts:
                                if script not in ep_scripts:
                                    ep_scripts.append(scripts)
                        else:
                            ep_scripts = scripts

                        self.distribution.entry_points["console_scripts"] = ep_scripts

                bdist_wheel_base_class.finalize_options(self)
        dist.cmdclass["bdist_wheel"] = bdist_wheel_rust_extension



def rust_extensions(dist, attr, value):
    assert attr == "rust_extensions"

    orig_has_ext_modules = dist.has_ext_modules
    dist.has_ext_modules = lambda: (
        orig_has_ext_modules() or bool(dist.rust_extensions)
    )

    if dist.rust_extensions:
        add_rust_extension(dist)
