#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# the Docker and Docker Compose packages in the repositories are too old to work with this project - install the latest versions instead
sudo apt-get install --yes -qq curl
sudo apt-get purge --yes -qq lxc-docker docker.io docker-compose # remove old packages that can cause conflicts
curl -fsSL https://get.docker.com/ | sh # install Docker
curl -L https://github.com/docker/compose/releases/download/1.6.0/docker-compose-`uname -s`-`uname -m` | sudo tee /usr/local/bin/docker-compose > /dev/null
sudo chmod +x /usr/local/bin/docker-compose # install Docker Compose
sudo usermod -aG docker ${USER} # add the current user to the Docker group (required in order to run the Docker daemon without sudo)

# we still need sudo even though we've been added to the Docker group here, since the group change only takes effect after logging out and logging in again
sudo docker-compose run web ${DIR}/../manage.py collectstatic # collect all the static files to /app/static, required by the tests
sudo docker-compose run web ${DIR}/../manage.py test # run the test suite real quick
