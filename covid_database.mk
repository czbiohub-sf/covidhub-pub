TEST_DB_CONTAINER_NAME = cliahub-local-test
TEST_DB_CONTAINER_ID = $(shell docker ps -a | grep $(TEST_DB_CONTAINER_NAME) | awk '{print $$1}')
TEST_DB_CONTAINER_RUNNING_ID = $(shell docker ps | grep $(TEST_DB_CONTAINER_NAME) | awk '{print $$1}')

.PHONY: lambda-zip lambda-deploy create-test-db start-test-db stop-test-db drop-local-dbs tests

ifeq ($(ENV),staging)
DATABASE_LAMBDA_NAME=cliahub-database-populator-staging
else ifeq ($(ENV),prod)
DATABASE_LAMBDA_NAME=cliahub-database-populator
endif
# Ex: make lambda-deploy-database ENV=staging
lambda-deploy-database:
ifndef ENV
	$(error ENV is undefined. Set to staging or prod)
else ifneq ($(DATABASE_LAMBDA_NAME),)
	@aws lambda update-function-code --function-name $(DATABASE_LAMBDA_NAME) --zip-file fileb://code/lambda_function.zip --publish | cat
	GIT_INFO=$$(echo `git rev-parse --short --verify HEAD` `git rev-parse --abbrev-ref HEAD` `git tag --points-at HEAD`) && \
	URL=$$(aws secretsmanager get-secret-value --secret-id covid-19/slack_url --query SecretString --output text) && \
	curl -X POST --data-urlencode "payload={'channel': '#covid19data_ops', 'text': \"[rds_$$ENV] Deployed: $$GIT_INFO\"}" $$URL;
endif

create-test-db:
	@if [ "$(TEST_DB_CONTAINER_ID)" == "" ]; then \
		docker create --name $(TEST_DB_CONTAINER_NAME) -p 5432:5432 \
		-e POSTGRES_USER='cliahub' \
		-e POSTGRES_PASSWORD='cliahub' \
		-e POSTGRES_DB='cliahub' \
		postgres:11.5-alpine; \
	fi

start-test-db:
	@if [ "$(TEST_DB_CONTAINER_ID)" == "" ]; then $(MAKE) create-test-db; fi
	@if [ "$(TEST_DB_CONTAINER_RUNNING_ID)" == "" ]; then \
		docker start $(TEST_DB_CONTAINER_NAME) && sleep 2; \
	fi

stop-test-db:
	docker stop $(TEST_DB_CONTAINER_NAME)

drop-local-dbs:
	@if [ "$(TEST_DB_CONTAINER_RUNNING_ID)" != "" ]; then $(MAKE) stop-test-db; fi
	@( read -p "Delete all local databases containers? [y/N]: " sure && case "$$sure" in [yY]) true;; *) false;; esac )
	docker rm --force $(TEST_DB_CONTAINER_NAME) || true

unit-tests-covid-database:
	pytest -n4 code/covid_database
