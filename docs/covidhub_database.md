# qPCR Database

This repository contains the code for the qPCR database, which runs on AWS Lambda and writes to an RDS instance.

## Testing

We use pytest for testing. You can set up a test database in a local Docker container:

```bash
make create-test-db # to create the database container named 
make start-test-db # to start
make stop-test-db # to stop
make drop-local-db # to remove the container
```

There is a CLI defined in `covid_database.scripts.cliadb.py`. When the database is running you can create the tables with `cliadb create`, and populate them with some test data with `cliadb populate`. You may need to set the environment variable `INPUT_GDRIVE_PATH` to the path of the Google Drive where all the files are stored. For production, it is `Covid19`.

### Autocompletion for cliadb

To install command completion for the cliadb command, refer to [this guide](https://click.palletsprojects.com/en/7.x/bashcomplete/) from the Click docs. e.g. to install autocompletion for `zsh`:

```
_CLIADB_COMPLETE=source_zsh cliadb > cliadb-complete.sh
. cliadb-complete.sh  # or configure this to run when you activate the env
```

## The lambda

As with [qpcr_processing](https://github.com/czbiohub/qpcr_processing), there are two lambdas (staging and prod) running to populate the database(s). Deploying is a similar procedure as in the other repo:

```
make lambda-zip
make lambda-deploy-database ENV=[prod or staging]
``` 

This will deploy to the following lambdas

| Lambda Function Name                       | Description |
|--------------------------------------------|-------------|
| cliahub-database-populator | This script populates the production RDS database at 3 am and 3 pm |
| cliahub-database-populator-staging | A staging version of the database for verifying that things are working |

## Interacting with RDS

RDS credentials are stored in AWS Secrets using their template.

| Secret ID | Description |
|-----------|-------------|
| cliahub/cliahub_test_db | Credentials for the localhost db (default) |
| cliahub/cliahub_rds_prod | Read-write access to the CLIAHub RDS |
| cliahub/cliahub_rds_read_prod | Read-only access to the CLIAHub RDS |
| cliahub/cliahub_rds_staging | Read-write access to the CLIAHub staging RDS |
| cliahub/cliahub_rds_read_staging | Read-only access to the CLIAHub staging RDS |

By default `cliadb` will connect to the DB in the local docker container, but you can specify a different RDS with the `--db-secret` argument: 

```bash
cliadb --db-secret cliahub/cliahub_rds_prod populate
```

### Connecting directly to RDS

You can connect directly to RDS by using `psql` and the info in the secrets:

```bash
psql -h [RDS_url_from_secrets] -U [RDS_user] cliahub
```

then enter the password when prompted.

## Setting up database users and permissions

The local testing databases have a superuser setup automatically. For staging and production databases, here's how to setup and configure user permissions.

These instructions assume you're using `psql` - please read the inline comments for how to set passwords without `psql`.

### Create users, set passwords and modify default `public` schema

These commands create database users and only need to be run when the database is first created, not when tables or schemas are dropped.

```sql
-- The cliahub user will be read-only, while cliahub_rw will be read write
CREATE USER cliahub;
-- If using psql, set the user password
\password cliahub
-- Alternatively, you can store a md5hashed password by replacing the CREATE USER line with:
-- CREATE USER cliahub WITH PASSWORD 'md5<output>';
-- where <output> is the result of echo -n ${PASSWORD}cliahub | md5sum

CREATE USER cliahub_rw;
-- In psql, set password, or set the password directly as above if not using psql
\password cliahub_rw 
```

Next, revoke the ability to create tables in the `public` schema from the role `PUBLIC`, which all users inherit, and prevent the `PUBLIC` role from connecting to the database, meaning users by default can't connect unless explicitly assigned one of the roles we create.

```sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE cliahub FROM PUBLIC;
```

### Grant permissions to users

This follows the guidelines at https://aws.amazon.com/blogs/database/managing-postgresql-users-and-roles/, except we don't bother creating roles and instead set permissions directly on our two users, since those are the only ones we'll use.

The `ALTER` lines should set permissions correctly for future tables added to our schema, but if the entire schema is re-created, these permissions modifications will need to be re-run.

```sql
-- Grant read-only permissions to cliahub user
GRANT CONNECT ON DATABASE cliahub TO cliahub;
GRANT USAGE ON SCHEMA qpcr_processing TO cliahub;
GRANT USAGE ON SCHEMA ngs_sample_tracking TO cliahub;
-- Grants SELECT permission to existing tables in our schemas
GRANT SELECT ON ALL TABLES IN SCHEMA qpcr_processing TO cliahub; 
GRANT SELECT ON ALL TABLES IN SCHEMA ngs_sample_tracking TO cliahub; 
-- ALTER default privileges so the cliahub user can select future tables created in our schemas.
ALTER DEFAULT PRIVILEGES IN SCHEMA qpcr_processing GRANT SELECT ON TABLES TO cliahub; 
ALTER DEFAULT PRIVILEGES IN SCHEMA ngs_sample_tracking GRANT SELECT ON TABLES TO cliahub; 

-- Grant read-write permissions to cliahub_rw user
GRANT CONNECT ON DATABASE cliahub TO cliahub_rw;
GRANT USAGE, CREATE ON SCHEMA qpcr_processing TO cliahub_rw;
GRANT USAGE, CREATE ON SCHEMA ngs_sample_tracking TO cliahub_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA qpcr_processing TO cliahub_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ngs_sample_tracking TO cliahub_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA qpcr_processing GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cliahub_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA ngs_sample_tracking GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cliahub_rw;
-- read-write users also need to be able to modify sequences, i.e., for auto-incrementing counters
GRANT USAGE ON ALL SEQUENCES IN SCHEMA qpcr_processing TO cliahub_rw;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ngs_sample_tracking TO cliahub_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA qpcr_processing GRANT USAGE ON SEQUENCES TO cliahub_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA ngs_sample_tracking GRANT USAGE ON SEQUENCES TO cliahub_rw;
```
