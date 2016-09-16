.PHONY: creds

creds:
	@docker-compose run web ./manage.py add_google_credentials \
		--client-id="$(CLIENT_ID)" --client-secret="$(CLIENT_SECRET)"
