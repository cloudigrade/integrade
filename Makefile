PYTEST_OPTIONS = -vvv

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
	@echo "  clean             Remove all saved logs and cached python files"

all: lint test-coverage

install:
	pip install .

install-dev:
	pip install -e .[dev]

lint:
	flake8 integrade tests

test:
	py.test tests

test-api:
	py.test $(PYTEST_OPTIONS) integrade/tests/api/v1

clean:
	rm -f *.log
	rm -f *.xml
	PYCLEAN_PLACES=${PYCLEAN_PLACES:-'.'}
	find ${PYCLEAN_PLACES} -type f -name "*.py[co]" -delete
	find ${PYCLEAN_PLACES} -type d -name "__pycache__" -delete


UI_DRIVER ?= Chrome 
UI_BROWSER ?= Chrome

test-ui:
	py.test $(PYTEST_OPTIONS) integrade/tests/ui \
	--driver $(UI_DRIVER) --capability browserName $(UI_BROWSER) \

test-coverage:
	py.test --verbose --cov-report term --cov=integrade --cov=tests tests

docs:
	scripts/gendocs.sh

.PHONY: all install install-dev lint test test-coverage test-api docs
