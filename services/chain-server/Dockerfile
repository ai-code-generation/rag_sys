ARG BASE_IMAGE_URL=nvcr.io/nvidia/base/ubuntu
ARG BASE_IMAGE_TAG=22.04_20240212

FROM ${BASE_IMAGE_URL}:${BASE_IMAGE_TAG}

ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND noninteractive

# Install required ubuntu packages for setting up python 3.10
RUN apt update && \
    apt install -y curl software-properties-common libgl1 libglib2.0-0 && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt update && apt install -y python3.10 && \
    apt-get clean

# Install pip for python3.10
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

RUN rm -rf /var/lib/apt/lists/*

# Uninstall build packages
RUN apt autoremove -y curl software-properties-common

# Copy requirements and install dependencies
COPY requirements.txt /opt/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/requirements.txt

# Set environment variables needed for Text splitter
RUN mkdir /tmp-data/; mkdir /tmp-data/nltk_data/
RUN chmod 777 -R /tmp-data
RUN chown 1000:1000 -R /tmp-data
ENV NLTK_DATA=/tmp-data/nltk_data/
ENV HF_HOME=/tmp-data

# Install nltk packages to avoid runtime download
RUN python3.10 -m nltk.downloader averaged_perceptron_tagger
RUN python3.10 -m nltk.downloader stopwords
RUN python3.10 -m nltk.downloader punkt
RUN python3.10 -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('Snowflake/snowflake-arctic-embed-l'); model.save('/tmp-data')"

# Copy chain server source code
COPY . /opt/chain_server

WORKDIR /opt/chain_server
ENTRYPOINT ["uvicorn", "server:app"]
