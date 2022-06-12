CURDIR=$(abspath .)

# These three are passed in from nox.
BUILDROOT ?= $(CURDIR)/builddir
PYMAJORMINORMICRO ?= 3.11.0
PYPRERELEASE ?= b1# I'm not sure how to split 3.11.0b1 in Make.


EMSCRIPTEN_VERSION ?= 3.1.13
EMSCRIPTEN_VERSION_UNDERSCORE := $(subst .,_,$(EMSCRIPTEN_VERSION:v%=%))

export PLATFORM_TRIPLET=wasm32-emscripten
export SYSCONFIG_NAME=_sysconfigdata__emscripten_$(PLATFORM_TRIPLET)
export PLATFORM=emscripten_$(EMSCRIPTEN_VERSION_UNDERSCORE)_wasm32


export EMSDKDIR = $(BUILDROOT)/emsdk

# BASH_ENV tells bash to source emsdk_env.sh on startup.
export BASH_ENV := $(CURDIR)/env.sh
# Use bash to run each command so that env.sh will be used.
SHELL := /bin/bash


# Set version variables.
version_tuple := $(subst ., ,$(PYMAJORMINORMICRO:v%=%))
PYMAJOR=$(word 1,$(version_tuple))
PYMINOR=$(word 2,$(version_tuple))
PYMICRO=$(word 3,$(version_tuple))
PYVERSION=$(PYMAJORMINORMICRO)$(PYPRERELEASE)
PYMAJORMINOR=$(PYMAJOR).$(PYMINOR)


PYTHONURL=https://www.python.org/ftp/python/$(PYMAJORMINORMICRO)/Python-$(PYVERSION).tgz
PYTHONTARBALL=$(BUILDROOT)/downloads/Python-$(PYVERSION).tgz
PYTHONBUILD=$(BUILDROOT)/build/Python-$(PYVERSION)

PYTHONLIBDIR=$(BUILDROOT)/install/Python-$(PYVERSION)/lib
PYTHONINCLUDEDIR=$(BUILDROOT)/install/Python-$(PYVERSION)/include

NAMESPACE_PACKAGE_DIST_DIR=../examples/namespace_package/dist
NAMESPACE_PACKAGE_WHEEL_NAME=namespace_package-0.1.0-cp$(PYMAJOR)$(PYMINOR)-cp$(PYMAJOR)$(PYMINOR)-$(PLATFORM).whl
NAMESPACE_PACKAGE_WHEEL_PATH=$(NAMESPACE_PACKAGE_DIST_DIR)/$(NAMESPACE_PACKAGE_WHEEL_NAME)

export CARGO_HOME ?= $(HOME)/.cargo
export CARGO_BUILD_TARGET=wasm32-unknown-emscripten
export CARGO_TARGET_WASM32_UNKNOWN_EMSCRIPTEN_LINKER=$(CURDIR)/emcc_wrapper.py
export PYO3_CONFIG_FILE=$(CURDIR)/pyo3_config.ini
export RUSTFLAGS=\
	-C relocation-model=pic \
	-C target-feature=+mutable-globals \
	-C link-arg=-sSIDE_MODULE=1 \
	-C link-arg=-sWASM_BIGINT 
	

all: libpython

namespace_package_wheel: $(NAMESPACE_PACKAGE_WHEEL_PATH)

python-interpreter: interpreter/main.js

libpython: $(PYTHONLIBDIR)/libpython$(PYMAJORMINOR).a

$(BUILDROOT)/.exists: 
	mkdir -p $(BUILDROOT)
	touch $@


# Install emscripten
$(EMSDKDIR)/.exists : $(BUILDROOT)/.exists
	git clone https://github.com/emscripten-core/emsdk.git --depth 1 --branch $(EMSCRIPTEN_VERSION) $(EMSDKDIR)
	$(EMSDKDIR)/emsdk install $(EMSCRIPTEN_VERSION)
	cd $(EMSDKDIR)/upstream/emscripten && cat $(CURDIR)/emscripten_patches/* | patch -p1
	$(EMSDKDIR)/emsdk activate $(EMSCRIPTEN_VERSION)
	touch $(EMSDKDIR)/.exists


$(PYTHONTARBALL):
	[ -d $(BUILDROOT)/downloads ] || mkdir -p $(BUILDROOT)/downloads
	wget -q -O $@ $(PYTHONURL)

$(PYTHONBUILD)/.patched: $(PYTHONTARBALL)
	[ -d $(PYTHONBUILD) ] || ( \
		mkdir -p $(dir $(PYTHONBUILD));\
		tar -C $(dir $(PYTHONBUILD)) -xf $(PYTHONTARBALL) \
	)
	touch $@

$(PYTHONBUILD)/Makefile: $(PYTHONBUILD)/.patched $(EMSDKDIR)/.exists
	cd $(PYTHONBUILD) && \
	CONFIG_SITE=Tools/wasm/config.site-wasm32-emscripten \
	PLATFORM_TRIPLET="$(PLATFORM_TRIPLET)" \
  	emconfigure ./configure -C \
		--host=wasm32-unknown-emscripten \
		--build=$(shell $(PYTHONBUILD)/config.guess) \
		--with-emscripten-target=browser \
		--enable-wasm-dynamic-linking \
		--with-build-python=python3.11

$(PYTHONLIBDIR)/libpython$(PYMAJORMINOR).a : $(PYTHONBUILD)/Makefile
	cd $(PYTHONBUILD) && \
		emmake make -j3 libpython$(PYMAJORMINOR).a

	# Generate sysconfigdata
	_PYTHON_SYSCONFIGDATA_NAME=$(SYSCONFIG_NAME) _PYTHON_PROJECT_BASE=$(PYTHONBUILD) python3.11 -m sysconfig --generate-posix-vars

	mkdir -p $(PYTHONINCLUDEDIR)
	mkdir -p $(PYTHONLIBDIR)/python$(PYMAJORMINOR)
	mkdir -p $(PYTHONLIBDIR)/sysconfigdata/
	# Copy libexpat.a, libmpdec.a, and libpython3.11.a
	# In noxfile, we explicitly link libexpat and libmpdec via RUSTFLAGS
	find $(PYTHONBUILD) -name '*.a' -exec cp {} $(PYTHONLIBDIR) \;
	# Install Python stdlib
	cp -r $(PYTHONBUILD)/Lib/* $(PYTHONLIBDIR)/python$(PYMAJORMINOR)
	cp -r $(PYTHONBUILD)/Include/* $(PYTHONINCLUDEDIR)
	cp -r $(PYTHONBUILD)/pyconfig.h $(PYTHONINCLUDEDIR)
	cp `cat pybuilddir.txt`/$(SYSCONFIG_NAME).py $(PYTHONLIBDIR)/python$(PYMAJORMINOR)
	cp `cat pybuilddir.txt`/$(SYSCONFIG_NAME).py $(PYTHONLIBDIR)/sysconfigdata/


interpreter/main.js: $(PYTHONLIBDIR)/libpython$(PYMAJORMINOR).a interpreter/main.c interpreter/pre.js
	cd interpreter && emcc -c main.c -o main.o -I$(PYTHONINCLUDEDIR) -fPIC
	cd interpreter &&  \
	emcc main.o -o main.js \
		-L$(PYTHONLIBDIR) \
		-lpython$(PYMAJORMINOR) \
		-lmpdec \
		-lexpat \
		-s MAIN_MODULE=1 \
		-s WASM_BIGINT \
		--preload-file $(PYTHONLIBDIR)/python$(PYMAJORMINOR)@/lib/python$(PYMAJORMINOR) \
		--pre-js pre.js \
		-lnodefs.js



$(NAMESPACE_PACKAGE_WHEEL_PATH) : $(PYTHONLIBDIR)/libpython$(PYMAJORMINOR).a
	cd ../examples/namespace_package && \
		RUSTUP_TOOLCHAIN=nightly \
		_SETUPTOOLSRUST_BUILD_STD=1 \
		PYTHONPATH=$(PYTHONLIBDIR)/sysconfigdata/ \
		_PYTHON_SYSCONFIGDATA_NAME=$(SYSCONFIG_NAME) \
		_PYTHON_HOST_PLATFORM=$(PLATFORM) \
		python setup.py bdist_wheel


clean:
	rm -rf $(BUILDROOT)
