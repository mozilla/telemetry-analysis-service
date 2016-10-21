.PHONY: build clean creds migrate shell static stop test up

help:
	@echo "Welcome to the Telemetry Analysis Service\n"
	@echo "The list of commands for local development:\n"
	@echo "  build      Builds the docker images for the docker-compose setup"
	@echo "  clean      Stops and removes all docker images and purge the collected static files"
	@echo "  creds CLIENT_ID=<CLIENT_ID> CLIENT_SECRET=<CLIENT_SECRET>"
	@echo "             Sets the Google Credentials required for authentication"
	@echo "  migrate    Runs the Django database migrations"
	@echo "  redis-cli  Opens a Redis CLI"
	@echo "  shell      Opens a Bash shell"
	@echo "  static     Collects static files (only needed in rare circumstances such as DEBUG=False)"
	@echo "  test       Runs the Python test suite"
	@echo "  up         Runs the whole stack, served under http://localhost:8000/\n"
	@echo "  stop       Stops the docker containers"

build:
	docker-compose build

clean: stop
	docker-compose rm -f
	rm -rf static/

creds:
	@docker-compose run web ./manage.py add_google_credentials \
	--client-id="$(CLIENT_ID)" --client-secret="$(CLIENT_SECRET)"

migrate:
	docker-compose run web ./manage.py migrate --run-syncdb

shell:
	docker-compose run web bash

redis-cli:
	docker-compose run redis redis-cli -h redis

static:
	# this is only necessary after adding/removing/editing static files
	docker-compose run web python manage.py collectstatic --noinput

stop:
	docker-compose stop

test: static
	docker-compose run web pytest

up:
	docker-compose up
