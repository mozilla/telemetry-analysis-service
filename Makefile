.PHONY: build clean creds migrate shell static test up

creds:
	@docker-compose run web ./manage.py add_google_credentials \
		--client-id="$(CLIENT_ID)" --client-secret="$(CLIENT_SECRET)"

build:
	docker-compose build

clean:
	docker-compose rm -f
	rm -rf static/

migrate:
	docker-compose run web ./manage.py migrate --run-syncdb

shell:
	docker-compose run web bash

static:
	# this is only necessary after adding/removing/editing static files
	docker-compose run web ./manage.py collectstatic --noinput

test: static
	docker-compose run web ./manage.py test

up:
	docker-compose up
