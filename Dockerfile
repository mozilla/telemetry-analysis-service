FROM debian:jessie

EXPOSE 8000

RUN adduser --uid 1000 --disabled-password --gecos '' --no-create-home webdev

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential python python-dev python-pip \
                                               libpq-dev postgresql-client gettext sqlite3 && \
    rm -rf /var/lib/apt/lists/*

# Using PIL or Pillow? You probably want to uncomment next line
# RUN apt-get update && apt-get install -y --no-install-recommends libjpeg8-dev

WORKDIR /app

# Get pip8
COPY bin/pipstrap.py bin/pipstrap.py
RUN ./bin/pipstrap.py

# First copy requirements.txt and peep so we can take advantage of
# docker caching.
COPY requirements.txt /app/requirements.txt
RUN pip install -U pip && pip install --require-hashes --no-cache-dir -r requirements.txt

COPY . /app
RUN chown webdev.webdev -R .
USER webdev
