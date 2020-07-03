import json

import boto3


def get_db_uri(secret_id: str = "cliahub/cliahub_rds_read_prod") -> str:
    """Provides a URI for the database based on an AWS secret id. By default this
    function will set up read-only access to the RDS. The CLI uses a test db instead.

    Parameters
    ----------
    :param secret_id: The name of the secret stored on AWS. Options are:
        - cliahub/cliahub_test_db - credentials for a local testing container
        - cliahub/cliahub_rds_prod - read/write access to the RDS instance
        - cliahub/cliahub_rds_read_prod - read-only access to the RDS instance (default)
        - cliahub/cliahub_rds_staging - read/write access to the RDS instance
        - cliahub/cliahub_rds_read_staging - read-only access to the RDS instance (default)
    """

    client = boto3.client("secretsmanager", region_name="us-west-2")

    return "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
        **json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])
    )
