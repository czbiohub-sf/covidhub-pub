SHELL := /bin/bash

include comet.mk
include covid_database.mk
include qpcr_processing.mk


setup-develop:
	pip install -e code'[dev]'
	pre-commit install


# lambda-zip to prepare your deployment package.
# GIT_HEAD contains the sha, branch, and any tags.
lambda-zip:
	@git diff-index --quiet HEAD -- || (echo "Please commit or stash changes before zipping" && exit 1)
	cd code && ( \
		rm -f lambda_function.zip && \
		echo `git rev-parse --short --verify HEAD` `git rev-parse --abbrev-ref HEAD` `git tag --points-at HEAD` >| qpcr_processing/GIT_HEAD && \
		git ls-tree -z -r --name-only HEAD | xargs -0 zip -r9 lambda_function.zip qpcr_processing/GIT_HEAD && \
		rm qpcr_processing/GIT_HEAD \
	)

style: lint black isort

lint:   lint-non-init lint-init

GENERALLY_IGNORED_WARNINGS=E203, E231, E501, W503

lint-non-init:
	flake8 --ignore "$(GENERALLY_IGNORED_WARNINGS)" --exclude='*__init__.py' code

lint-init:
	flake8 --ignore "$(GENERALLY_IGNORED_WARNINGS), F401" --filename='*__init__.py' code

black:
	black --check code

isort:
	isort -rc --check code
.PHONY: style lint lint-non-init lint-init black isort

unit-tests: unit-tests-covid-database unit-tests-qpcr-processing unit-tests-comet
.PHONY: unit-tests
