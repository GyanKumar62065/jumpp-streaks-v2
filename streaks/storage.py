"""S3 adapter (Floci locally). The only module that calls S3. S3 is the durable copy of all input."""

import json
import time
import uuid
from datetime import datetime

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

_INPUTS_PREFIX = "inputs/"
_RAW_POSTS_PREFIX = "raw/posts/"
_CONNECT_ATTEMPTS = 30
_CONNECT_DELAY_S = 1


class Storage:
    def __init__(self, client, bucket: str):
        self._client = client
        self._bucket = bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def put_input_file(self, name: str, body: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=_INPUTS_PREFIX + name, Body=body)

    def get_input_file(self, name: str) -> bytes:
        return self._client.get_object(Bucket=self._bucket, Key=_INPUTS_PREFIX + name)["Body"].read()

    def put_raw_post(self, body: bytes, received_at: datetime) -> str:
        """Archive a POST body with the server receive time, so a replay can reuse it."""
        key = f"{_RAW_POSTS_PREFIX}{received_at:%Y-%m-%d}/{received_at:%H%M%S%f}-{uuid.uuid4().hex}.json"
        envelope = {"received_at": received_at.isoformat(), "body": body.decode("utf-8", errors="replace")}
        self._client.put_object(Bucket=self._bucket, Key=key, Body=json.dumps(envelope).encode())
        return key

    def get_raw_posts(self) -> list[tuple[datetime, bytes]]:
        """(received_at, body) for every archived POST, oldest key first."""
        keys = []
        for page in self._client.get_paginator("list_objects_v2").paginate(Bucket=self._bucket, Prefix=_RAW_POSTS_PREFIX):
            keys += [item["Key"] for item in page.get("Contents", [])]
        posts = []
        for key in sorted(keys):
            envelope = json.loads(self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read())
            posts.append((datetime.fromisoformat(envelope["received_at"]), envelope["body"].encode()))
        return posts


def open_storage(endpoint_url: str, bucket: str) -> Storage:
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 10, "mode": "standard"}),
    )
    return Storage(client, bucket)


def open_storage_when_ready(endpoint_url: str, bucket: str) -> Storage:
    """Floci has no compose healthcheck, so retry until the bucket exists."""
    storage = open_storage(endpoint_url, bucket)
    for _ in range(_CONNECT_ATTEMPTS - 1):
        try:
            storage.ensure_bucket()
            return storage
        except Exception:  # connection refused while Floci boots
            time.sleep(_CONNECT_DELAY_S)
    storage.ensure_bucket()  # last attempt: let its error surface
    return storage
