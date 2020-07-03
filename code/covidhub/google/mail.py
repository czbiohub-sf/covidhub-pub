import base64
import logging
import mimetypes
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import BinaryIO, Mapping

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_service(google_credentials: service_account.Credentials, sender: str):
    delegated_credentials = google_credentials.with_scopes(
        ["https://www.googleapis.com/auth/gmail.send"]
    ).with_subject(sender)
    return build(
        "gmail", "v1", credentials=delegated_credentials, cache_discovery=False
    )


def send_email(
    google_credentials: service_account.Credentials,
    sender: str,
    recipients: str,
    subject: str,
    body: str,
    attachments: Mapping[str, BinaryIO],
):
    """
    Send a reporting email with link to the output spreadsheet

    Parameters
    ----------
    google_credentials : service_account.Credentials
        Credentials to the service account
    sender : str
        sender of the message
    recipients : str
        Recipients of the message, separated by commas.
    subject : str
        subject line of the message
    body : str
        text of the body of the message
    attachments : Mapping[str, BinaryIO]
        attachment files, as a dictionary of { filename: file-like }
    """
    if not recipients:
        logger.info("No recipients, skipping email")
        return

    logger.info(f"Formatting email to send to: {recipients}")

    service = get_service(google_credentials, sender)

    message = _format_message(
        sender=sender,
        recipients=recipients,
        subject=subject,
        body=body,
        attachments=attachments,
    )
    _send_message(service=service, user_id="me", message=message)


def _send_message(service, user_id, message):
    try:
        message = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )
        logger.info(msg=f"Email sent id: {message['id']}")
        return message
    except Exception:
        logger.exception(msg="An error occurred when sending the email")


def _format_message(
    sender: str,
    recipients: str,
    subject: str,
    body: str,
    attachments: Mapping[str, BinaryIO],
):
    """
    Helper function to format an email. `attachment_files` should be a dictionary
    mapping from filenames to file data (some sort of file-like bytes object)

    :param sender:
    :param recipients:
    :param subject: subject line of the message
    :param body: text of the body of the message
    :param attachments: attachment files, as a dictionary of { filename: file-like }
    """
    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = recipients
    message["Subject"] = subject

    # f"[CLIAHUB Report] Sample plate {barcode} Results"
    message.attach(MIMEText(body))

    for filename, attachment_data in attachments.items():
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        main_type, sub_type = content_type.split("/", 1)

        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase(main_type, sub_type)
        attachment_data.seek(0)
        part.set_payload(attachment_data.read())

        # Add header as key/value pair to attachment part
        part.add_header(
            "Content-Disposition", "attachment", filename=filename,
        )
        message.attach(part)

    raw = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
    raw = raw.decode("utf-8")
    return {"raw": raw}
