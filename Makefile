SRC_DIR := src
BUILD_DIR := yc_build
BUILD_ARC := yc_build.zip

build:
	mkdir -p $(BUILD_DIR)
	cp -r $(SRC_DIR)/* $(BUILD_DIR)
	cp requirements.txt $(BUILD_DIR)
	cp YandexInternalRootCA.crt $(BUILD_DIR)
	zip -j $(BUILD_ARC) $(BUILD_DIR)/*
	rm -rf $(BUILD_DIR)

clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(BUILD_ARC)


migration:
	alembic revision --autogenerate

migrate:
	alembic upgrade head

# This is a phony target, meaning it doesn't represent a file
.PHONY: build clean migration migrate