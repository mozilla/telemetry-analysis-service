FROM debian:jessie

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app/

RUN set -x \
    && apt-get update \
    && apt-get install locales -y \
    && locale-gen en_US.UTF-8

EXPOSE 8000

RUN adduser --uid 1000 --disabled-password --gecos '' --no-create-home webdev

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential python python-dev python-pip libpq-dev \
        postgresql-client gettext sqlite3 libffi-dev \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# Get pip8
COPY bin/pipstrap.py bin/pipstrap.py
RUN ./bin/pipstrap.py

COPY requirements.txt /tmp/requirements.txt

RUN set -x \
    && pip install -U pip setuptools \
    && pip install -r /tmp/requirements.txt \
    && find /usr/local -type f -name '*.pyc' -name '*.pyo' -delete \
    && rm -rf ~/.cache/

COPY . /app

RUN chown webdev.webdev -R .
USER webdev
