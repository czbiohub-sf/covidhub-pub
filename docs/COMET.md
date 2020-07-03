### Workflow diagram

![workflow](images/covid19-mNGS-workflow.png)

---

![wells](images/wells-layout.png)

---

## Helpful inks

* [COMET SOP: Google Forms](https://docs.google.com/document/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit)
* [Draft tracking fields breakdown](https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=1254298329)

## How to deploy the Lambda

1.  Start at the repository root.
2.  `make lambda-zip`
3.  `make lambda-deploy-comet`
4.  You can view and debug in the [Lambda dashboard](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/comet-dev?tab=configuration), in conjunction with test form submissions. The CloudWatch Log Group is [/aws/lambda/comet-dev](https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#logStream:group=/aws/lambda/comet-dev;streamFilter=typeLogStreamPrefix).

## How to deploy the Google Apps Script

1.  Go to [mNGS_sample_tracking](https://script.google.com/a/chanzuckerberg.com/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit) project in Google Apps Script. Ask Angela if you need permission. Open `Code.gs`.
2.  Copy-and-paste the contents of `apps_script.gs` into `Code.gs` to replace it.
3.  Click the `Save` icon.
4.  Do test runs by submitting your forms and viewing the Execution logs [here](https://script.google.com/home/projects/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/executions). You can use `console.log` to debug.

## How to update Lambda Python dependencies

1.  Take a look at the instructions to update the [covid-lims-layer](https://github.com/czbiohub/qpcr_processing_lambda_layer).

## Input/output files example

* End-to-end example of using the forms flow, not including text fields.
* Numbers (1:, 2:, 3:, 4:) refer to the folder numbers in [COVID19_mNGS_forms](https://drive.google.com/drive/u/1/folders/1biG9QX_Z9UBxE2lbztjlVFR-zmSfvDUV).

### **1 - COMET Sample Arrival (`sample_database`)**

* Input:
  * User uploaded metadata file:
    * 1 (File responses): `*.xlsx` (N/A for internal samples, this example)
* Output:
  * 1: `OG_plates.xlsx` (appended)

### **2 - COMET Input Plate (`draw_96_plate_map`)**

**Form Path 1: Select CZB_IDs -> New plate map**

* Input (over multiple submissions):
  * User uploaded sample ID file (lists of CZB_IDs):
    * 2 (File responses): `COMET96-W-R020.xlsx`
    * 2 (File responses): `COMET96-W-R021.xlsx`
    * 2 (File responses): `COMET96-W-R022.xlsx`
  * 1: `OG_plates.xlsx`
* Output:
  * 2: `COMET96-W-R020.csv`
  * 2: `COMET96-W-R021.csv`
  * 2: `COMET96-W-R022.csv`

**Form Path 2: Use existing plate map -> New plate map**

* Input:
  * User uploaded "96 COMET Source Plate File (OG or RX)"
* Output:
  * New plate map, e.g. `COMET96-W-R020.csv`

**Form Path 3: Cherry-pick from ripe_samples by Accession -> New plate map**

* Input:
  * User uploaded "96 COMET Sample Accessions file" (a list of Accessions to pluck)
  * 1: `ripe_samples.xlsx`
* Output:
  * New plate map, e.g. `COMET96-W-R020.csv`

### **3 - COMET 384 Plate Map (`concat_96_384`)**

* Input:
  * 2: `COMET96-W-R020.csv`
  * 2: `COMET96-W-R021.csv`
  * 2: `COMET96-W-R022.csv`
  * 1: `OG_plates.xlsx`
* Output:
  * 3: `COMET384-L-007.csv`

### **4 - COMET Index Plates (`bind_index_plate`)**

* Input:
  * 3: `COMET384-L-007.csv`
  * User uploaded index plate file:
    * 4 (File responses): `DBP_10 - Sabrina Mann.xlsx`
* Output:
  * 4: `COMET384_SEQ007_DBP-10_MiSeqNovaSeq.csv`
  * 4: `COMET384_SEQ007_DBP-10_iSeqNextSeq.csv`

example local command:
`comet bind-index \ --plate "code/test/data/COMET384-L-007.csv" \ --index-map "code/test/data/DBP_10 - Sabrina Mann.xlsx" \ --tracking-name "384_SEQ007_DBP-10`

## How to add a new Form and script/backend

1.  Work with Angela and the users to create a new Form in [COVID19_mNGS_forms](https://drive.google.com/drive/u/1/folders/1biG9QX_Z9UBxE2lbztjlVFR-zmSfvDUV).
2.  Update `apps_script.gs` with a new block. Add allowed `params` to be passed along. Get it deployed.
    * Tip: Make sure to use the Tab/Table name in Sheets, and the actual column title, such as `Please upload the metadata associated with the OG plate`.
3.  Add another action route to `code/app.py`.
4.  Create a new handling file in `code/lib`. Current signatures follow `def function_name(drive_service, sheets_service, event_body={})`.
    * The params will appear in `event_body`, as in `plate_name = event_body["384 COMET Sequencing Plate Name"]`.

## Debugging tips

An interactive debugging loop could look like:

1.  See error in Slack channel.
1.  Go to the [CloudWatch Logs](https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#logStream:group=/aws/lambda/comet-dev;streamFilter=typeLogStreamPrefix) for the Lambda and investigate.
1.  Find the triggering form submit in [mNGS_sample_tracking](https://docs.google.com/spreadsheets/u/1/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=14720283)
1.  Reproduce by submitting the same form contents again. Keep the tab open.
1.  Make bug fixes / logging outputs in the [Lambda console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/comet-dev?tab=configuration). Save changes. (Optional: Temporarily change the channel in `slack.py` to reduce noise.)
1.  Re-submit by refreshing the Form confirmation tab. Debug and repeat until the problem is solved.
1.  Commit changes and open a PR.
