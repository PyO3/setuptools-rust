Build manylinux1 wheels
-----------------------------

.. code-block:: bash

    docker run --rm -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /io/build-wheels.sh
