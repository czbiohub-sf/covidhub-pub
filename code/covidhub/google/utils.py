import json

import boto3
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from google_auth_httplib2 import AuthorizedHttp
from gspread import Client
from httplib2 import Http
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry


def get_secrets_manager_credentials(
    secret_id: str = "covid-19/google_creds",
) -> service_account.Credentials:
    client = boto3.client("secretsmanager", region_name="us-west-2")
    secret_string = client.get_secret_value(SecretId=secret_id)["SecretString"]

    return service_account.Credentials.from_service_account_info(
        json.loads(secret_string)
    )


def get_gspread_connection(
    credentials: service_account.Credentials,
    max_retries=7,
    backoff_factor=0.5,
    status_forcelist=frozenset([403, 413, 429, 503]),
) -> Client:
    scoped_credentials = credentials.with_scopes(
        [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    retry = Retry(
        total=max_retries,
        read=max_retries,
        connect=max_retries,
        status=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = Session()
    session.mount("https://", adapter)

    gc = Client(auth=scoped_credentials, session=session)
    gc.session = AuthorizedSession(scoped_credentials)
    return gc


def update_sheet(spread_sheet, sheet_name, data):
    spread_sheet.values_update(
        f"{sheet_name}!A1", params={"valueInputOption": "RAW"}, body={"values": data}
    )


def new_http_client_from_service(service) -> Http:
    """Given a service object, return a new HTTP client with the same credentials and
    scope as the service object."""
    return AuthorizedHttp(service._http.credentials)
