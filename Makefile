help:
	@echo "Please use \`make <target>' where <target> is one of:"
	@echo "  help            to show this message"
	@echo "  all             to to execute lint and test-coverage"
	@echo "  install         to install integrade to run integration tests"
	@echo "  install-dev     to install integrade in editable mode to develop"
	@echo "                  test cases"
	@echo "  lint            to lint the source code"
	@echo "  test            to run integrade's framework unit tests"
	@echo "  test-coverage   to run integrade's unit tests and measure test"
	@echo "                  coverage"

all: lint test-coverage

install:
	pip install .

install-dev:
	pip install -e .[dev]

lint:
	flake8 .

test:
	py.test tests

test-coverage:
	py.test --verbose --cov-report term --cov=integrade --cov=tests tests

.PHONY: all install install-dev lint test test-coverage
