EXAMPLE_FILES_DIR = example_files
EXAMPLE_WELL_LIT = '$(EXAMPLE_FILES_DIR)/20200319-174657_SP000001_tube_to_plate.csv'
EXAMPLE_PLATE_LAYOUT = '$(EXAMPLE_FILES_DIR)/96sample_plate_accessions_SP000214.xlsx'
EXAMPLE_BARCODE = D041758
EXAMPLE_BARCODE2 = B131885

TESTING_GDRIVE_PATH = testing_qPCR_results
PROD_GDRIVE_PATH = Covid19
TESTING_ACCESSION_TRACKING_SHEET = "Testing Accession Tracking"
TESTING_CLIN_LAB_REPORTING_SHEET = "Testing Clin Lab Reporting"
TESTING_PLATE_QUEUE_SHEET = "Supervisor Plate Queue Testing"


update-deps:
ifndef description
	$(error Please provide a description for the update)
endif
	docker build . -t qpcr-deps -f layer_dockerfile
	CONTAINER_ID=$$(docker run -d qpcr-deps false) && \
	docker cp $$CONTAINER_ID:/dep_layer.zip dep_layer.zip && \
	docker rm $$CONTAINER_ID
	@aws lambda publish-layer-version \
	--layer-name cliahub-lims-deps \
	--description "$(description)" \
	--zip-file fileb://dep_layer.zip \
	--compatible-runtimes python3.7


# Ex: make lambda-deploy-processing ENV=staging
lambda-deploy-processing:
ifndef ENV
	$(error ENV is undefined. Set to dev, staging, or prod)
endif
	@aws lambda update-function-code --function-name covid_lims-${ENV}-check_sheets --zip-file fileb://code/lambda_function.zip --publish | cat
	@if [ $$ENV = "prod" ] || [ $$ENV = "staging" ]; then \
		GIT_INFO=$$(echo `git rev-parse --short --verify HEAD` `git rev-parse --abbrev-ref HEAD` `git tag --points-at HEAD`) && \
		URL=$$(aws secretsmanager get-secret-value --secret-id covid-19/slack_url --query SecretString --output text) && \
		curl -X POST --data-urlencode "payload={\"channel\": \"#covid19data_ops\", \"text\": \"[$$ENV] Deployed: $$GIT_INFO\"}" $$URL; \
	fi


ifeq ($(ENV),staging)
ACCESSION_LAMBDA_NAME=covid-accession-tracking-staging
else ifeq ($(ENV),prod)
ACCESSION_LAMBDA_NAME=covid-accession-tracking
endif
# Ex: make lambda-deploy-accession-tracking ENV=staging
lambda-deploy-accession-tracking:
ifndef ENV
	$(error ENV is undefined. Set to dev, staging, or prod)
else ifneq ($(ACCESSION_LAMBDA_NAME),)
	$(MAKE) accession-tests
	@aws lambda update-function-code --function-name $(ACCESSION_LAMBDA_NAME) --zip-file fileb://code/lambda_function.zip --publish | cat
	GIT_INFO=$$(echo `git rev-parse --short --verify HEAD` `git rev-parse --abbrev-ref HEAD` `git tag --points-at HEAD`) && \
	URL=$$(aws secretsmanager get-secret-value --secret-id covid-19/slack_url --query SecretString --output text) && \
	curl -X POST --data-urlencode "payload={\"channel\": \"#covid19data_ops\", \"text\": \"[$$ENV-accession] Deployed: $$GIT_INFO\"}" $$URL
endif


# Ex: make lambda-invoke ENV=staging
lambda-invoke:
ifndef ENV
	$(error ENV is undefined. Set to dev, staging, or prod)
endif
	aws lambda invoke --function-name covid_lims-${ENV}-check_sheets output.txt

unit-tests-qpcr-processing:
	pytest -n2 -m "not (integtest or accession or local_processing or full_processing)" code/qpcr_processing

integration-tests:
	pytest -n2 -m integtest code

accession-tests:
	pytest -m accession code

local-processing-tests:
	pytest -n2 -m local_processing code

full-processing-tests:
	pytest -m full_processing code

tests: \
 unit-tests-qpcr-processing \
 integration-tests \
 local-processing-tests \
 full-processing-tests


# Run through all available accession data
test-compile-accessions:
	INPUT_GDRIVE_PATH=$(PROD_GDRIVE_PATH) \
	OUTPUT_GDRIVE_PATH=$(TESTING_GDRIVE_PATH) \
	ACCESSION_TRACKING_SHEET=$(TESTING_ACCESSION_TRACKING_SHEET) \
	CLIN_LAB_REPORTING_SHEET=$(TESTING_CLIN_LAB_REPORTING_SHEET) \
	PLATE_QUEUE_SHEET=$(TESTING_PLATE_QUEUE_SHEET) \
	qpcr_processing compile_accessions \
	--updates-only


test-compile-accessions-local:
	INPUT_GDRIVE_PATH=$(PROD_GDRIVE_PATH) \
	ACCESSION_TRACKING_SHEET=$(TESTING_ACCESSION_TRACKING_SHEET) \
	CLIN_LAB_REPORTING_SHEET=$(TESTING_CLIN_LAB_REPORTING_SHEET) \
	PLATE_QUEUE_SHEET=$(TESTING_PLATE_QUEUE_SHEET) \
	qpcr_processing compile_accessions \
	--sample-barcodes SP000147 SP000001 SP000136 SP000226 \
	--run-path $(EXAMPLE_FILES_DIR)

test-local:
	qpcr_processing local \
	--protocol SOP-V1 \
	--qpcr-run-path $(EXAMPLE_FILES_DIR) \
	--barcode $(EXAMPLE_BARCODE) \
	--well-lit $(EXAMPLE_WELL_LIT)

test-local-protocol2:
	qpcr_processing local \
	--protocol SOP-V2 \
	--qpcr-run-path $(EXAMPLE_FILES_DIR) \
	--barcode $(EXAMPLE_BARCODE2) \
	--plate-layout $(EXAMPLE_PLATE_LAYOUT)

test-gdrive:
	echo `git rev-parse --short --verify HEAD` `git rev-parse --abbrev-ref HEAD` `git tag --points-at HEAD` >| code/qpcr_processing/GIT_HEAD
	INPUT_GDRIVE_PATH=$(TESTING_GDRIVE_PATH) \
	OUTPUT_GDRIVE_PATH=$(TESTING_GDRIVE_PATH) \
	qpcr_processing gdrive; errcode=$$?; rm code/qpcr_processing/GIT_HEAD; exit $$errcode
