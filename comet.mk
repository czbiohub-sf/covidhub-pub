# NOTE COMET IS CONFUSING BECAUSE comet-dev is actually the production lambda

# Ex: make lambda-deploy-comet ENV=staging
lambda-deploy-comet:
ifndef ENV
	$(error ENV is undefined. Set to staging or dev)
endif
	@aws lambda update-function-code --function-name comet-${ENV} --zip-file fileb://code/lambda_function.zip --publish | cat
	@if [ $$ENV = "dev" ]; then \
		GIT_INFO=$$(echo `git rev-parse --short --verify HEAD` `git rev-parse --abbrev-ref HEAD` `git tag --points-at HEAD`) && \
		URL=$$(aws secretsmanager get-secret-value --secret-id covid-19/slack_url --query SecretString --output text) && \
		curl -X POST --data-urlencode "payload={\"channel\": \"#covid19data_ops\", \"text\": \"[comet_$$ENV] Deployed: $$GIT_INFO\"}" $$URL; \
	fi

unit-tests-comet:
	pytest -n2 code/comet
