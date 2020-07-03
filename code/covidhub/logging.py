import datetime
import hashlib
import json
import logging
import sys

import boto3
import requests

from covidhub.config import Config


class SlackLogFilter:
    def __init__(self, cfg: Config):
        self.aws_env = cfg.aws_env
        self.max_minute_rate = int(cfg["SLACK"]["max_minute_rate"])

        # cloudwatch client for throttling
        self.cw_client = boto3.client(
            "cloudwatch", region_name=cfg["AWS"].get("region")
        )
        self.cw_namespace = cfg["AWS"].get("cloudwatch_namespace")

    def filter(self, record: logging.LogRecord):
        if getattr(record, "notify_slack", False):
            if record.exc_info is not None:
                metric_name = record.exc_info[0].__name__
            else:
                sha = hashlib.sha256(
                    f"{self.aws_env}-{record.msg}".encode()
                ).hexdigest()[:8]
                metric_name = f"slack_message_{sha}"

            if self.get_recent_metric_sum(metric_name, self.max_minute_rate) > 0:
                print(f"Suppressed Slack message: {record.msg}")
                return False
            else:
                self.put_metric(metric_name, 1)
                return True
        else:
            return False

    def put_metric(self, name: str, value: int = 1):
        """Send a metric data point to CloudWatch."""
        try:
            resp = self.cw_client.put_metric_data(
                Namespace=self.cw_namespace,
                MetricData=[{"MetricName": name, "Value": value}],
            )
            return resp
        except Exception as err:
            print(f"Error in adding metric: {err}")

    def get_recent_metric_sum(self, name: str, past_minutes: int):
        """Get the sum of a given CloudWatch metric in the past window."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        start_time = now - datetime.timedelta(minutes=past_minutes)
        resp = self.cw_client.get_metric_statistics(
            Namespace=self.cw_namespace,
            MetricName=name,
            StartTime=start_time,
            EndTime=now,
            Period=60 * past_minutes,
            Statistics=["Sum"],
        )
        count = 0
        if "Datapoints" in resp and len(resp["Datapoints"]):
            # Should be only one datapoint if the period is equal to the time window
            count = resp["Datapoints"][0]["Sum"]
        return count


class SlackLogHandler(logging.Handler):
    def __init__(self, cfg: Config):
        super(SlackLogHandler, self).__init__()

        self.webhook_url = cfg["SLACK"]["url"]
        self.channel = cfg["SLACK"]["alert_channel"]

    def emit(self, record: logging.LogRecord):
        text = self.format(record)
        payload = {"channel": self.channel, "text": text}
        requests.post(self.webhook_url, json.dumps(payload).encode("utf-8"))


def create_logger(cfg: Config, debug: bool = False):
    log = logging.getLogger()

    # google is noisy, turn up its logging level
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    # botocore logs secret strings via debug (!), silence those
    logging.getLogger("botocore").setLevel(logging.INFO)

    # remove all existing handlers, including any set up by AWS or any handlers
    # from previous runs in this process
    for old_handler in list(log.handlers):
        log.removeHandler(old_handler)

    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    # Need to modify logger to output INFO level to stdout for cloudwatch/local runs
    stream_handler = logging.StreamHandler(sys.stdout)
    if debug:
        stream_handler.setLevel(logging.DEBUG)
    else:
        stream_handler.setLevel(logging.INFO)
    stream_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    stream_handler.setFormatter(stream_formatter)

    log.addHandler(stream_handler)
    log.info(msg="Added stream handler")

    if cfg["SLACK"].get("enabled", "").lower() == "true":
        slack_handler = SlackLogHandler(cfg)
        slack_handler.setLevel(logging.CRITICAL)
        slack_formatter = logging.Formatter(f"[{cfg.aws_env}] %(message)s")
        slack_handler.setFormatter(slack_formatter)
        slack_cloudwatch_filter = SlackLogFilter(cfg)
        slack_handler.addFilter(slack_cloudwatch_filter)

        log.addHandler(slack_handler)
        log.info(msg="Added slack handler")
