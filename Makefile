include .env

SRC_DIR := src
BUILD_DIR := yc_build
BUILD_ARC := yc_build.zip

build:
	mkdir -p $(BUILD_DIR)
	rsync -a --exclude='__pycache__/' --exclude='flytwo.egg-info/' $(SRC_DIR)/ $(BUILD_DIR)
	cp requirements.txt $(BUILD_DIR)
	cp YandexInternalRootCA.crt $(BUILD_DIR)
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
	curl --request POST --url https://api.telegram.org/bot${BOT_TOKEN}/setWebhook --header 'content-type: application/json' --data '{"url": "${CLOUD_FUNC_BOT_HOOK_URL}"}'

delete_hook:
	curl --request POST --url 'https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook'

test:
	python -m pytest -n 16 tests

# This is a phony target, meaning it doesn't represent a file
.PHONY: build clean migration migrate set_hook delete_hook test
