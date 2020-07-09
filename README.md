# COVIDHub

This repository contains multiple projects related to the COVID19 work going on at the Biohub.

*This public version of the repo is missing test data (which contains real test results) and credentials for Google Drive and AWS. We hope that the code base and architecture may nevertheless prove useful for others.*

## Projects

Sourcecode for these projects is located in the `code` directory. Detailed READMEs are in the `docs` directory.

 - `covidhub`: core libraries, infrastructure, etc
 - `qpcr_processing`: pipeline and other tools for processing the results of COVID19 qPCR tests
 - `comet`: pipeline for NGS sequencing pipeline and sample tracking
 - `covidhub_database`: the models and populators for the database, which includes both qPCR and NGS.


## Setting up development

 1. Create a Python 3.7 environment using your preferred environment-creating tool.
 1. Clone the repository and run `pip install -e code'[dev]'` to install dependencies and development tools (quotes are needed for `zsh` users).
    * This should install cleanly, otherwise raise an issue.
    * If you don't want an editable install, remove the `-e` option.
 1. Run `pre-commit install` to install the hook into your repo.
 1. These steps are also available in one make command: `make setup-develop`.

When you `git commit` the hook will run `black` on any files you modified. If it ends up reformatting anything, it will abort the commit, and you will need to try again. But the second time will work! For more about `black` style you can read [here](https://black.readthedocs.io/en/stable/the_black_code_style.html).

## Getting set up to run tests

The command line tools will attempt to fetch Google Drive credentials from AWS. Therefore you will need AWS credentials configured in your environment, with access the AWS secrets for this project (double cloud!). If this isn't working ask in Slack.

If you can get credentials from AWS, `make tests` should run successfully. If not, please raise this in Slack.
