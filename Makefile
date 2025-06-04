SRC_FILES := $(wildcard src/cbs_analyzer/*.py)

format:
	black $(SRC_FILES)

black: format

check_black_version:
	black --version

install_black:
	pip install black