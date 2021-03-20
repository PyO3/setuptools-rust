FROM rustembedded/cross:x86_64-unknown-linux-gnu-0.2.1

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.6 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1
