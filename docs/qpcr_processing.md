# qPCR Processing

This repository is focused on processing the results of CLIAHub testing and formatting PDF results to send to the clinical lab.

## Running Commands
After you `pip install` the project, the command `qpcr_processing` will be available. It has multiple subcommands:

```
> qpcr_processing --help
usage: qpcr_processing [-h] [--debug] [--secret-id SECRET_ID]
                       {local,gdrive,compile_accessions,notify_results} ...

positional arguments:
  {local,gdrive,compile_accessions,notify_results}

optional arguments:
  -h, --help            show this help message and exit
  --debug
  --secret-id SECRET_ID
```

The `--debug` flag will change the logging level to be more verbose (a very small increase at the moment). The argument `--secret-id` can be used to access an alternate secret, e.g. `qpcr_processing --secret_id 'covid-19/google_test_creds'` will use the same credentials as GitHub Actions.

| Subcommand         | Summary                                               |
|--------------------|-------------------------------------------------------| 
| local              | Generate a report from local files                    |
| gdrive             | Run entirely from gdrive, read and write              |
| compile_accessions | Create a table of accessions and their current status |
| notify_results     | Send a notification that test results are ready       |

### Generating a report locally

To generate a report locally, obtain the log files (see below) and the plate map file. Then run `qpcr_processing local` (usage below):

```
> qpcr_processing local --help
usage: qpcr_processing local [-h] --qpcr-run-path QPCR_RUN_PATH
                             [--protocol PROTOCOL] [--barcode BARCODE]
                             [--control-layout CONTROL_LAYOUT] [--use-gdrive]
                             [--plate-layout PLATE_MAP_FILE | --well-lit PLATE_MAP_FILE | --hamilton PLATE_MAP_FILE]

optional arguments:
  -h, --help            show this help message and exit
  --qpcr-run-path QPCR_RUN_PATH
  --protocol PROTOCOL
  --barcode BARCODE
  --control-layout CONTROL_LAYOUT
  --use-gdrive
  --plate-layout PLATE_MAP_FILE
  --well-lit PLATE_MAP_FILE
  --hamilton PLATE_MAP_FILE
```

An example command line would be:
```
qpcr_processing local --qpcr-run-path example_files --barcode B131275 --protocol SOP-V1 --well-lit example_files/20200319-174657_SP000001_tube_to_plate.csv
```

With the `--use-gdrive` option, it will try to retrieve the log files, metadata, plate layout, and control wells from Google Drive. You can also provide a layout file and/or controls file to overwrite those values. The output will be written to `--qpcr-run-path`. You must supply a barcode (otherwise it would attempt to process all the files to date)
```
qpcr_processing local --use-gdrive --qpcr-run-path example_files --barcode B131275
```

#### Getting the log files

The script `fetch_barcodes` will download the necessary files from the log folder and put them in a local directory:

```
usage: fetch_barcodes [-h] [--output-dir OUTPUT_DIR]
                      barcodes [barcodes ...]

positional arguments:
  barcodes

optional arguments:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
```

For example to (re)download all the example files:

```
fetch_barcodes --output-dir example_files D041758 D041772 B131275
```

#### Running a custom set of control wells

The `--control-layout` argument allows you pass custom control wells. Create a `csv` file with the customized wells with the format `well_id,control_type` (no header). A common layout is LOD (NTC on both A and H columns), so a file for that is available as `example_files/validation_controls.csv`.

## The Lambdas

The following Lambda functions are used by our processing pipeline. You can view them in the [AWS Management Console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions)

| Lambda Function Name                       | Description |
|--------------------------------------------|-------------|
| covid_lims-{prod,staging,dev}-check_sheets | The main processing script that checks for qPCR results, runs `processing.py`, reads metadata from gdrive and produces reports |
| covid_lims-{prod,dev}-notify               | Email processed results out, see [qpcr_processing/notify](https://github.com/czbiohub/qpcr_processing/blob/master/code/qpcr_processing/notify/) |
| covid_lims-{prod,dev}-database             | Parse Google Sheets and populate our RDS database. This code lives in `code/covid_database`. |
| covid-plate-layout-formatting	             | Generate a plate map PDF when they submit a layout to Sample Plate Metada, see [make_layout_pdf](https://github.com/czbiohub/qpcr_processing/blob/master/code/qpcr_processing/scripts/make_layout_pdf.py) |
| covid-accession-tracking                   | Tracking lambda that reads from forms responses and qpcr processing results to create 3 different tracking sheets for lab staff [accession_tracking](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/covid-accession-tracking?tab=configuration) | 

For the `check_sheets` Lambda:

* `prod`:
  * checks marker files in `Covid19/Pipeline Results`,
  * reads qPCR results and plate maps from the main `Covid19` gdrive,
  * reads the main `Covid19` spreadsheets, and,
  * writes results to `Covid19/Pipeline Results`.
* `staging`:
  * checks marker files in `staging_output/Pipeline Results`,
  * reads qPCR results and plate maps from the main `Covid19` gdrive,
  * reads the main `Covid19` spreadsheets, and,
  * writes results to `staging_output/Pipeline Results` on gdrive.
* `dev`:
  * reads qPCR results and plate maps from the main `testing_qPCR_Results` gdrive,
  * reads the main `Covid19` spreadsheets, and,
  * writes results to `testing_qPCR_Results/Pipeline Results` on gdrive.

Note that the spread sheets in `testing_qPCR_Results` are deprecated and not currently read by any of the lambdas.

For the `accession_tracking` Lambda:

* `prod`:
    * Gets deployed in tandem with `covid_lims-prod-check-sheets`
    * Gets run every 10min. 
    * Reads from `Covid19` gdrive
    * Writes to: 
        * [Plate Queue Tracking Sheet](https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=0)
        * [Verbose Accession Tracking Sheet](https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=0)
        * [Clin Lab Reporting Sheet](https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=0)
* `staging`
    * Gets deployed in tandem with `covid_lims-staging-check-sheets`
    * Runs only on demand for testing
    * Reads from `Covid19`
    * Writes to:
        * [Plate Queue Testing](https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=0)
        * [Accession Tracking Verbose Testing](https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=1994795228)
        * [Clin Lab Reporting Testing](https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=1994795228)

### Processing Lambda environment variables

| Variable name        | Description                                                                      |
|----------------------|----------------------------------------------------------------------------------|
| GDRIVE_PATH          | Path to the folder holding the PCR inputs, with path component separated by `/`. |
| RECEIVER_EMAILS      | Email addresses where the reports are sent to, separated by commas.              |
| SENDER_EMAIL         | Email address where reports are sent from.                                       |

### Lambda layer and dependencies
- See the [qpcr_processing_lambda_layer README](https://github.com/czbiohub/qpcr_processing_lambda_layer/).

### How to disable Slack notifications
1. Go to the [Lambda console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/covid_lims-prod-check_sheets?tab=configuration) for the Function.
1. Set `SLACK_ENABLED` to `False` (or any value besides `True` in any capitalization). Save.
1. Update `#covid19data_ops` with a new pinned post for visibility.
1. Remember to re-enable promptly in the `prod` env after resolving issues.

### How to disable Lambda continuous trigger
1. Go to the [Lambda console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/covid_lims-prod-check_sheets?tab=configuration) for the Function.
1. Under `Designer` on the left, click the box `CloudWatch Events/EventBridge`.
1. In the box on the bottom, switch the toggle from `Enabled` to `Disabled`.
1. Update `#covid19data_ops` with a new pinned post for visibility.
1. Remember to re-enable promptly in the `prod` env after resolving issues.

### How to adjust the Lambda event trigger rate
1. CLI examples:
    - `aws events put-rule --name covid_lims-prod-trigger --schedule-expression "rate(1 minute)"`
    - `aws events put-rule --name covid_lims-prod-trigger --schedule-expression "rate(30 minutes)"`
2. Alternatively, update manually in the [CloudWatch console](https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#rules:name=covid-lims_check-sheets).
3. Update `#covid19data_ops` with a new pinned post for visibility.
    - Currently default in `prod` is 1 minute.
    - Remember to re-enable promptly in the `prod` env after resolving issues.

### How to deploy to the `covid_lims-dev-check_sheets` lambda to test your changes

Example with `dev`:
1. Check on Slack if anyone is using `covid_lims-dev-check_sheets` on Slack and, if not, tell folks you're using it
1. (Optional) Configure the Lambda environment variables for your use case via  [AWS Management Console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions) 
   * In particular, you may want to change `RECEIVER_EMAILS` to send yourself the results PDF. The results are also written to the `testing_qPCR_Results` gdrive as described [below](#how-to-check-script-run-results)
1. Start at the repository root on your branch.
1. `make lambda-zip`
1. `make lambda-deploy-processing ENV=dev`
1. Run a test from the CLI
    1. `make lambda-invoke ENV=dev`
1. OR run a test from the AWS Lambda console dashboard
    1. Open up the corresponding [Function page](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions)
    1. If you see `Select a test event` in the upper-right, click into the dropdown and create one called `Event1`. The name and trigger contents don't actually matter with the current setup.
    1. Click `Save` if active. Click `Test` to run your code. Check the `Execution Results` panel that appears.
    1. To debug interactively, make changes in the `Function code` section, `Save`, `Test`, repeat.

### How to check script run results

Example workflow we have been using (paths may vary): 
1. Go to `GDRIVE_PATH` (ex: `testing_qPCR_results`) in Google Drive.
1. Go to `qPCR results` / `processing_markers`.
    1. Remove a marker file for the sample you want to run  (e.g. `D000000`). The marker file name shows that the file has been processed.
1. Invoke your test run, as above.
1. If email environmental variables are set `RECEIVER_EMAILS` and `SENDER_EMAIL` you should recieve an email from `XXXXXX` with sample reports.
1. You should see a new final report csv (e.g. `D000000-results.csv`) in the gdrive folder specified in `code/config.ini`for `pcr_results_folder`

### Deploying to `covid_lims-prod-check_sheets` 
#### Night Before the Release
1. Check out latest version of master and tag it `git tag -a YYYY-MM-DD -m "{RELEASE_MESSAGE}"`
2. Make deployment zip `make lambda-zip`
3. Check to see if the changes require adding a new lib. If so follow instructions [Here](https://github.com/czbiohub/qpcr_processing_lambda_layer/) to add them to our staging lambda. 
4. Run `make lambda-deploy-processing ENV=staging`
5. Run a full test on staging
    - Go to [staging output](https://drive.google.com/drive/u/0/folders/150XVMSwcfaAB1mznIxVtvPBdp4fBDL5f)
    - Delete one or two marker files from the `processing_markers` folder
    - Go to [staging-lambda](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/covid_lims-staging-check_sheets?tab=configuration)
    - Make sure it has the code you just deployed 
    - Click `Test`
    - If Execution result: succeeded, verify that everything ran smoothly by checking out the logs for the run in CloudWatch
7. Push the tag `git push origin {TAG_NAME}`
8. Let everyone know the release testing passed and link to the tag to be released. 
#### Release Day 
1. If you made layer modifications to the staging lambda, make them to the [prod-lambda](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/covid_lims-prod-check_sheets?tab=configuration)
2. Deploy to the production Lambda:
   
   1. Verify that the staging build corresponding to `TAG_NAME` (e.g., what was created and pushed in [Night Before the Release](#night-before-the-release) above) is working
   2. Checkout the release tag
	  `git checkout {TAG_NAME}`
   3. Create the zip file for the deployment
	  `make lambda-zip`
   4. Deploy to `prod`
	  `make lambda-deploy-processing ENV=prod`
3. Let everyone know the release went smoothly with a slack message that includes some sick emojis
4. Relax 


### The Danger Zone

If something in the spreadsheets or main folders is broken and urgently needs to be fixed, you can log in as an `XXXXXX`. The password is stored in 1password and AWS Secrets. To copy to your clipboard:

```
make get-cliahub-admin-password
```

If you need more limited access (i.e. to modify files in the logs folder, which is still not to be taken lightly) you can retrieve the password for `XXXXXX`:

```
make get-cliahub-password
```


## Dependency Layer for AWS Lambda 

The dependencies for the package are installed in a layer: [cliahub-lims-deps](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/layers/cliahub-lims-deps/).

Dependencies are listed in `requirements.txt`, with the exception of `boto3` which is already in the lambda environment. `boto3` is instead listed as a dev dependency.

### Re-building the dependency layer

1. Add the new package (with version number) to `requirements.txt`.
1. Use the `make update-deps description=[description]` command, which builds `layer_dockerfile` to install all the dependencies and compress them, then uploads to AWS.
    1. Double-check your AWS Region is set to `us-west-2` (~/.aws/config).
    1. Remember to set your `AWS_PROFILE` if you have multiple AWS accounts.
    1. It may take a bit to upload. You should see a confirmation.
        1. It will fail if the zip file is >50MB and you may need to do some optimization on the installs.
        1. Possible optimizations include custom compilation (e.g. for numpy and pandas), removing tests/data, etc.
1. Go to the [staging Lambda console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/covid_lims-staging-check_sheets).
    1. Remove the old version from the stack.
    1. Click `Layers`. Click `Add a layer` with the `cliahub-lims-deps` version you just added. It will still be called `cliahub-lims-deps` but with a new version number.
    1. To test, you can put `import gspread` at the top of `processing.py`, for example.
    1. Click `Save` then `Test` in the upper-right. Verify there are no errors.
1. If your layer is invalid, go to the [Layers page](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/layers/cliahub-lims-deps/) and delete the unusable version. Remove the package locally if needed or install a different one.
1. If your layer is valid, go to the [prod Lambda console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/covid_lims-prod-check_sheets) and bump the layer version there, as above. Or, wait until your main code change reaches prod.

### Misc
- If you need to download a previous ZIP to verify contents, you can download from the [Layers page](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/layers/cliahub-lims-deps).
- Here is a helpful list of all the [modules that come preinstalled](https://gist.github.com/gene1wood/4a052f39490fae00e0c3) in the Lambda environment.

### What are the advantages of using Lambda Layers over a single deployment package?
- You can re-use the same layers across environments and projects to ensure consistency and save work. Layers are composable so you can mix-and-match.
- If you keep the "real" code deployment package under 3 MB, you retain the ability to edit and debug directly in the AWS Lambda console, which can come in handy.
