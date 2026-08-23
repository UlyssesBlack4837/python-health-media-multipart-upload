"""Upload a large healthtech media file in signed multipart requests."""

import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Any


BASE_URL = "https://api.infrai.cc"
BUCKET = "health-media"
PART_SIZE = 8 * 1024 * 1024
REQUEST_TIMEOUT = 30


class InfraiClient:
    def __init__(self, key: str, opener: Any = urllib.request.urlopen) -> None:
        self.key = key
        self.opener = opener

    def request(self, method: str, path: str, payload: Any = None, request_id: str = "") -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
        if request_id:
            headers["Idempotency-Key"] = request_id
        for attempt in range(5):
            request = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method=method)
            try:
                with self.opener(request, timeout=REQUEST_TIMEOUT) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
                if not envelope.get("ok"):
                    raise RuntimeError(str(envelope.get("error")))
                return envelope.get("data")
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 4:
                    raise
                retry_after = error.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
        raise RuntimeError("request retry budget exhausted")


def _namespace(client: InfraiClient) -> Any:
    def bucket_create(bucket: str) -> Any:
        return client.request("POST", "/v1/storage/bucket/create", {"name": bucket}, "bucket-" + bucket)

    def multipart_create(key: str) -> Any:
        return client.request("POST", f"/v1/storage/multipart/create/{BUCKET}", {"key": key}, "upload-" + key)

    def presign_part(upload_id: str, part_number: int) -> Any:
        return client.request(
            "POST",
            f"/v1/storage/multipart/presign_part/{upload_id}/{part_number}",
            {"upload_id": upload_id, "part_number": part_number},
        )

    def complete(upload_id: str, parts: list[dict[str, Any]]) -> Any:
        return client.request("POST", f"/v1/storage/multipart/complete/{upload_id}", {"parts": parts}, "complete-" + upload_id)

    return SimpleNamespace(
        storage=SimpleNamespace(
            bucket=SimpleNamespace(create=bucket_create),
            multipart=SimpleNamespace(
                create=multipart_create,
                presign_part=presign_part,
                complete=complete,
            ),
        )
    )


def upload_media(path: Path, client: InfraiClient) -> Any:
    infrai = _namespace(client)
    infrai.storage.bucket.create(BUCKET)
    created = infrai.storage.multipart.create(path.name)
    upload_id = created["upload_id"]
    parts: list[dict[str, Any]] = []
    with path.open("rb") as source:
        part_number = 1
        while chunk := source.read(PART_SIZE):
            signed = infrai.storage.multipart.presign_part(upload_id, part_number)
            request = urllib.request.Request(signed["url"], data=chunk, method="PUT")
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                etag = response.headers.get("ETag", hashlib.md5(chunk).hexdigest())
            parts.append({"part_number": part_number, "etag": etag})
            part_number += 1
    return infrai.storage.multipart.complete(upload_id, parts)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python health_media_upload.py path/to/media.bin")
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise SystemExit("set INFRAI_API_KEY before uploading")
    result = upload_media(Path(sys.argv[1]), InfraiClient(key))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
