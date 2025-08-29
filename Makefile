.PHONY: up down logs ps clean tokens

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

clean:
	docker compose down -v || true

tokens:
	@echo "ZAMMAD_TOKEN=$${ZAMMAD_TOKEN}"
	@echo "OPENPROJECT_API_KEY=$${OPENPROJECT_API_KEY}"
