# Changelog

## 1.5.2 (2022-09-19)
### Fixed
- Fix regression in `dylib` build artifacts not being found since 1.5.0. [#290](https://github.com/PyO3/setuptools-rust/pull/290)
- Fix regression in sdist missing examples and other supplementary files since 1.5.0. [#291](https://github.com/PyO3/setuptools-rust/pull/291)

## 1.5.1 (2022-08-14)
### Fixed
- Fix regression in `get_lib_name` crashing since 1.5.0. [#280](https://github.com/PyO3/setuptools-rust/pull/280)
- Fix regression in `Binding.Exec` builds with multiple executables not finding built executables since 1.5.0. [#283](https://github.com/PyO3/setuptools-rust/pull/283)

## 1.5.0 (2022-08-09)
### Added
- Add support for extension modules built for wasm32-unknown-emscripten with Pyodide. [#244](https://github.com/PyO3/setuptools-rust/pull/244)

### Changed
- Locate cdylib artifacts by handling messages from cargo instead of searching target dir (fixes build on MSYS2). [#267](https://github.com/PyO3/setuptools-rust/pull/267)
- No longer guess cross-compile environment using `HOST_GNU_TYPE` / `BUILD_GNU_TYPE` sysconfig variables. [#269](https://github.com/PyO3/setuptools-rust/pull/269)

### Fixed
- Fix RustBin build without wheel. [#273](https://github.com/PyO3/setuptools-rust/pull/273)
- Fix RustBin setuptools install. [#275](https://github.com/PyO3/setuptools-rust/pull/275)

## 1.4.1 (2022-07-05)
### Fixed
- Fix crash when checking Rust version. [#263](https://github.com/PyO3/setuptools-rust/pull/263)

## 1.4.0 (2022-07-05)
### Packaging
- Increase minimum `setuptools` version to 62.4. [#246](https://github.com/PyO3/setuptools-rust/pull/246)

### Added
- Add `cargo_manifest_args` to support locked, frozen and offline builds. [#234](https://github.com/PyO3/setuptools-rust/pull/234)
- Add `RustBin` for packaging binaries in scripts data directory. [#248](https://github.com/PyO3/setuptools-rust/pull/248)

### Changed
- `Exec` binding `RustExtension` with `script=True` is deprecated in favor of `RustBin`. [#248](https://github.com/PyO3/setuptools-rust/pull/248)
- Errors while calling `cargo metadata` are now reported back to the user [#254](https://github.com/PyO3/setuptools-rust/pull/254)
- `quiet` option will now suppress output of `cargo metadata`. [#256](https://github.com/PyO3/setuptools-rust/pull/256)
- `setuptools-rust` will now match `cargo` behavior of not setting `--target` when the selected target is the rust host. [#258](https://github.com/PyO3/setuptools-rust/pull/258)
- Deprecate `native` option of `RustExtension`. [#258](https://github.com/PyO3/setuptools-rust/pull/258)

### Fixed
- If the sysconfig for `BLDSHARED` has no flags, `setuptools-rust` won't crash anymore. [#241](https://github.com/PyO3/setuptools-rust/pull/241)

## 1.3.0 (2022-04-26)
### Packaging
- Increase minimum `setuptools` version to 58. [#222](https://github.com/PyO3/setuptools-rust/pull/222)

### Fixed
- Fix crash when `python-distutils-extra` linux package is installed. [#222](https://github.com/PyO3/setuptools-rust/pull/222)
- Fix sdist built with vendored dependencies on Windows having incorrect cargo config. [#223](https://github.com/PyO3/setuptools-rust/pull/223)

## 1.2.0 (2022-03-22)
### Packaging
- Drop support for Python 3.6. [#209](https://github.com/PyO3/setuptools-rust/pull/209)

### Added
- Add support for `kebab-case` executable names. [#205](https://github.com/PyO3/setuptools-rust/pull/205)
- Add support for custom cargo profiles. [#216](https://github.com/PyO3/setuptools-rust/pull/216)

### Fixed
- Fix building macOS arm64 wheel with cibuildwheel. [#217](https://github.com/PyO3/setuptools-rust/pull/217)

## 1.1.2 (2021-12-05)
### Changed
- Removed dependency on `tomli` to simplify installation. [#200](https://github.com/PyO3/setuptools-rust/pull/200)
- Improve error messages on invalid inputs to `rust_extensions` keyword. [#203](https://github.com/PyO3/setuptools-rust/pull/203)

## 1.1.1 (2021-12-01)
### Fixed
- Fix regression from `setuptools-rust` 1.1.0 which broke builds for the `x86_64-unknown-linux-musl` target. [#194](https://github.com/PyO3/setuptools-rust/pull/194)
- Fix `--target` command line option being unable to take a value. [#195](https://github.com/PyO3/setuptools-rust/pull/195)
- Fix regression from `setuptools-rust` 1.0.0 which broke builds on arm64 macos conda builds. [#196](https://github.com/PyO3/setuptools-rust/pull/196)
- Fix regression from `setuptools-rust` 1.1.0 which incorrectly converted library extension suffixes to the "abi3" suffix when `py_limited_api` was unspecified. [#197](https://github.com/PyO3/setuptools-rust/pull/197)

## 1.1.0 (2021-11-30)
### Added
- Add support for cross-compiling using [`cross`](https://github.com/rust-embedded/cross). [#185](https://github.com/PyO3/setuptools-rust/pull/185)

### Fixed
- Fix incompatibility with Python 3.6.0 using default values for NamedTuple classes. [#184](https://github.com/PyO3/setuptools-rust/pull/184)
- Stop forcing the `msvc` Rust toolchain for Windows environments using the `gnu` toolchain. [#187](https://github.com/PyO3/setuptools-rust/pull/187)

## 1.0.0 (2021-11-21)
### Added
- Add `--target` command line option for specifying target triple. [#136](https://github.com/PyO3/setuptools-rust/pull/136)
- Add new default `"auto"` setting for `RustExtension.py_limited_api`. [#137](https://github.com/PyO3/setuptools-rust/pull/137)
- Support very verbose cargo build.rs output. [#140](https://github.com/PyO3/setuptools-rust/pull/140)

### Changed
- Switch to `tomli` dependency. [#174](https://github.com/PyO3/setuptools-rust/pull/174)

### Removed
- Remove `test_rust` command. (`python setup.py test` is deprecated.) [#129](https://github.com/PyO3/setuptools-rust/pull/129)
- Remove `check_rust` command. [#131](https://github.com/PyO3/setuptools-rust/pull/131)
- Move `tomlgen_rust` command to separate `setuptools-rust-tomlgen` package. [#167](https://github.com/PyO3/setuptools-rust/pull/167)

### Fixed
- Use info from sysconfig when cross-compiling. [#139](https://github.com/PyO3/setuptools-rust/pull/139)
- Put Rust extension module binary under `build/lib.*` directory. [#150](https://github.com/PyO3/setuptools-rust/pull/150)
- Fix `Exec` binding with console scripts. [#154](https://github.com/PyO3/setuptools-rust/pull/154)

## 0.12.1 (2021-03-11)
### Fixed
- Fix some files unexpectedly missing from `sdist` command output. [#125](https://github.com/PyO3/setuptools-rust/pull/125)

## 0.12.0 (2021-03-08)
### Packaging
- Bump minimum Python version to Python 3.6.

### Added
- Support building x86-64 wheel on arm64 macOS machine. [#114](https://github.com/PyO3/setuptools-rust/pull/114)
- Add macOS universal2 wheel building support. [#115](https://github.com/PyO3/setuptools-rust/pull/115)
- Add option to cargo vendor crates into sdist. [#118](https://github.com/PyO3/setuptools-rust/pull/118)

### Changed
- Respect `PYO3_PYTHON` and `PYTHON_SYS_EXECUTABLE` environment variables if set. [#96](https://github.com/PyO3/setuptools-rust/pull/96)
- Add runtime dependency on setuptools >= 46.1. [#102](https://github.com/PyO3/setuptools-rust/pull/102)
- Append to, rather than replace, existing `RUSTFLAGS` when building. [#103](https://github.com/PyO3/setuptools-rust/pull/103)

### Fixed
- Set executable bit on shared library. [#110](https://github.com/PyO3/setuptools-rust/pull/110)
- Don't require optional `wheel` dependency. [#111](https://github.com/PyO3/setuptools-rust/pull/111)
- Set a more reasonable LC_ID_DYLIB entry on macOS. [#119](https://github.com/PyO3/setuptools-rust/pull/119)

## 0.11.6 (2020-12-13)

 - Respect `CARGO_BUILD_TARGET` environment variable if set. [#90](https://github.com/PyO3/setuptools-rust/pull/90)
 - Add `setuptools_rust.__version__` and require setuptools >= 46.1. [#93](https://github.com/PyO3/setuptools-rust/pull/93)

## 0.11.5 (2020-11-10)

 - Fix support for Python 3.5. [#86](https://github.com/PyO3/setuptools-rust/pull/86)
 - Fix further cases of building for 32-bit Python on 64-bit Windows. [#87](https://github.com/PyO3/setuptools-rust/pull/87)

## 0.11.4 (2020-11-03)

 - Fix `tomlgen` functionality on Windows. [#78](https://github.com/PyO3/setuptools-rust/pull/78)
 - Add support for building abi3 shared objects. [#82](https://github.com/PyO3/setuptools-rust/pull/82)

## 0.11.3 (2020-08-24)

 - Fix building on Linux distributions that use musl (e.g. Alpine) out of the box. [#80](https://github.com/PyO3/setuptools-rust/pull/80)

## 0.11.2 (2020-08-10)

 - Fix support for namespace packages. [#79](https://github.com/PyO3/setuptools-rust/pull/79)

## 0.11.1 (2020-08-07)

 - Fix building for 32-bit Python on 64-bit Windows. [#77](https://github.com/PyO3/setuptools-rust/pull/77)

## 0.11.0 (2020-08-06)

 - Remove python 2 support. [#53](https://github.com/PyO3/setuptools-rust/pull/53)
 - Fix compatibility with `cffi`. [#68](https://github.com/PyO3/setuptools-rust/pull/68)
 - Add support for pyo3 `0.12`'s `PYO3_PYTHON` setting. [#71](https://github.com/PyO3/setuptools-rust/pull/71)

## 0.10.6 (2018-11-07)

 - Fix tomlgen\_rust generating invalid `Cargo.toml` files.
 - Fix tomlgen\_rust setting wrong path in `.cargo/config`.

## 0.10.5 (2018-09-09)

 - Added license file [#41](https://github.com/PyO3/setuptools-rust/pull/41)

## 0.10.4 (2018-09-09)

 - Add `html-py-ever` example

## 0.10.3 (2018-09-06)

 - `path` in `RustExtension` now defaults to `Cargo.toml`

## 0.10.2 (2018-08-09)

 - Add `rustc_flags` and `verbose` as options
 - Adopted black code style
 - Moved changelog to markdown

## 0.10.0 (2018-05-06)

  - This release significantly improves performance

## 0.9.2 (2018-05-11)

  - Fix build\_rust crashing on Cargo.toml manifests without a name key
    in the \[lib\] section
  - Fix single quotes not being handled when parsing Cargo.toml

## 0.9.1 (2018-03-22)

  - Remove unicode\_literals import as Python 2 `distutils` does not
    support Unicode

## 0.9.0 (2018-03-07)

  - Find inplace extensions and automatically generate `Cargo.toml`
    manifests \#29

## 0.8.4 (2018-02-27)

  - Improve compatibility of build\_rust with build\_ext \#28

## 0.8.3 (2017-12-05)

  - Ignore strip option when platform is win32 \#26

## 0.8.2 (2017-09-08)

  - Fix script generation for bdist\_wheel

## 0.8.1 (2017-09-08)

  - Added native parameter
  - Fix script generation for executables

## 0.8.0 (2017-09-05)

  - Support multiple rust binaries \#24

## 0.7.2 (2017-09-01)

  - Generate console-script for Binding.Exec \#22
  - Do not run cargo check for sdist command \#18
  - Remove extra python3 file extension for executables.

## 0.7.1 (2017-08-18)

  - Allow to strip symbols from executable or dynamic library.
  - Use PyO3 0.2 for example.

## 0.7.0 (2017-08-11)

  - Allow to build executable and pack with python package.
  - Use PyO3 0.1 for example.

## 0.6.4 (2017-07-31)

  - check command respects optional option
  - Don't fail when Rust isn't installed while all extensions are
    optional

## 0.6.3 (2017-07-31)

  - Fix pypi source distribution

## 0.6.2 (2017-07-31)

  - Add optional option to RustExtension \#16

## 0.6.1 (2017-06-30)

  - Support CARGO\_TARGET\_DIR variable \#14

## 0.6.0 (2017-06-20)

  - Add support for PyO3 project <https://github.com/PyO3/PyO3>
  - Add support for no-binding mode

## 0.5.1 (2017-05-03)

  - Added support for "cargo test"
  - Fixed unbound method type error \#4

## 0.5.0 (2017-03-26)

  - Added support for "cargo check"

## 0.4.2 (2017-03-15)

  - Added "--qbuild" option for "build\_rust" command. Set "quiet" mode
    for all extensions.
  - Added "--debug" and "--release" options for "build\_rust" command.

## 0.4.1 (2017-03-10)

  - Fixed cargo manifest absolute path detection

## 0.4 (2017-03-10)

  - Fixed bdist\_egg and bdist\_wheel support
  - setuptool's clean command cleans rust project as well
  - Use absolute path to cargo manifest
  - Enable debug builds for inplace builds, otherwise build release
  - Simplify monkey patches

## 0.3.1 (2017-03-09)

  - Fix compatibility with some old versions of setuptools

## 0.3 (2017-03-09)

  - Fixed OSX extension compilation
  - Use distutils exceptions for errors
  - Add rust version check for extension
  - Cleanup example project

## 0.2 (2017-03-08)

  - Fix bdist\_egg and bdist\_wheel commands

## 0.1 (2017-03-08)

  - Initial release
