PYTEST_OPTIONS = -vvv
CLOUDIGRADE_USER=''

help:
	@echo "Please use \`make <target>' where <target> is one of:"
	@echo "  help              to show this message"
	@echo "  all               to to execute lint and test-coverage."
	@echo "  install           to install integrade if only running tests."
	@echo "  install-dev       to install integrade in editable mode to"
	@echo "                    develop test cases"
	@echo "  lint              to lint the source code"
	@echo "  test              to run integrade's framework unit tests"
	@echo "  test-coverage     to run integrade's unit tests and measure"
	@echo "                    test coverage"
	@echo "  test-api          to run functional tests against cloudigrade"
	@echo "                    api endpoints"

all: lint test-coverage

install:
	pip install .

install-dev:
	pip install -e .[dev]

lint:
	flake8 .

test:
	py.test tests

test-api:
	py.test $(PYTEST_OPTIONS) integrade/tests/api/v1

test-ui:
	py.test $(PYTEST_OPTIONS) integrade/tests/ui --driver=Firefox

test-all:
	py.test $(PYTEST_OPTIONS) integrade --driver=Firefox

test-coverage:
	py.test --verbose --cov-report term --cov=integrade --cov=tests tests

.PHONY: all install install-dev lint test test-coverage test-api
