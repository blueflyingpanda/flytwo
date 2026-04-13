include .env

SRC_DIR := src
BUILD_DIR := yc_build
BUILD_ARC := yc_build.zip

api:
	docker build -t flytwo-api -f Dockerfile.api .

build:
	mkdir -p $(BUILD_DIR)
	rsync -a --exclude='__pycache__/' --exclude='flytwo.egg-info/' $(SRC_DIR)/ $(BUILD_DIR)
	cd $(BUILD_DIR) && zip -r ../$(BUILD_ARC) *
	rm -rf $(BUILD_DIR)

clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(BUILD_ARC)


migration:
	alembic revision --autogenerate

migrate:
	alembic upgrade head

set_hook:
	curl --request POST --url https://api.telegram.org/bot${BOT_TOKEN}/setWebhook --header 'content-type: application/json' --data '{"url": "${API_URL}/webhook", "secret_token": "${TELEGRAM_SECRET}"}'

delete_hook:
	curl --request POST --url 'https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook'

test:
	uv run pytest -n 1 tests

# This is a phony target, meaning it doesn't represent a file
.PHONY: api build clean migration migrate set_hook delete_hook test
