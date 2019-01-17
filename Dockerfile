## Node container:

FROM node:10 as npm

WORKDIR /opt/npm
COPY package.json package-lock.json /opt/npm/
RUN npm install

## Python container:

FROM python:3.6-slim
LABEL maintainer="Jannis Leidel <jezdez@mozilla.com>"

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/ \
    DJANGO_CONFIGURATION=Prod \
    PORT=8000

EXPOSE $PORT

# add a non-privileged user for installing and running the application
# don't use --create-home option to prevent populating with skeleton files
RUN mkdir /app && \
    chown 10001:10001 /app && \
    groupadd --gid 10001 app && \
    useradd --no-create-home --uid 10001 --gid 10001 --home-dir /app app

# install a few essentials and clean apt caches afterwards
RUN mkdir -p \
        /usr/share/man/man1 \
        /usr/share/man/man2 \
        /usr/share/man/man3 \
        /usr/share/man/man4 \
        /usr/share/man/man5 \
        /usr/share/man/man6 \
        /usr/share/man/man7 \
        /usr/share/man/man8 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        apt-transport-https build-essential curl git gnupg libpq-dev \
        postgresql-client gettext sqlite3 libffi-dev  && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create static and npm roots
RUN mkdir -p /opt/npm /opt/static && \
    chown -R 10001:10001 /opt

# Install Python dependencies
COPY requirements/*.txt /tmp/requirements/
# Switch to /tmp to install dependencies outside home dir
WORKDIR /tmp
RUN pip install --no-cache-dir -r requirements/build.txt

USER 10001

# Copy Node dependencies from NPM container
COPY --from=npm /opt/npm /opt/npm

# Switch back to home directory
WORKDIR /app

COPY . /app

RUN DJANGO_CONFIGURATION=Build && \
    python manage.py collectstatic --noinput

# Using /bin/bash as the entrypoint works around some volume mount issues on Windows
# where volume-mounted files do not have execute bits set.
# https://github.com/docker/compose/issues/2301#issuecomment-154450785 has additional background.
ENTRYPOINT ["/bin/bash", "/app/bin/run"]

CMD ["web"]
