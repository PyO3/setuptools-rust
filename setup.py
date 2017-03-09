from setuptools import setup, find_packages

version = '0.2'


setup(
    name="setuptools-rust",
    version=version,
    author='Nikolay Kim',
    author_email='fafhrd91@gmail.com',
    url="https://github.com/fafhrd91/setuptools-rust",
    keywords='distutils setuptools rust',
    description="Setuptools rust extension plugin",
    long_description='\n\n'.join(
        (open('README.rst').read(), open('CHANGES.rst').read())),
    license='MIT',
    packages=['setuptools_rust'],
    zip_safe=True,
    classifiers=[
        "Topic :: Software Development :: Version Control",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
    ],
    entry_points="""
    [distutils.commands]
    build_rust=setuptools_rust:build_rust
    """
)
