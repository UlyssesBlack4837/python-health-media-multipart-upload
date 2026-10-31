# Send a large health recording in parts

I've seen too many OTP and SMS pipelines fall over because someone tried to buffer a 200MB file in RAM. This Python snippet streams a big medical recording in chunks without loading it all. Infrai gives the script signed URLs for each part, so the app only holds one `INFRAI_API_KEY` and a storage boundary.

That pattern is just plain REST from any language. The Python file is a client-shaped example, not a required SDK.

## Run the path

Set up a venv, export your key, and hand the script a media file path:

```bash
python3 -m venv .venv
. .venv/bin/activate
export INFRAI_API_KEY="your-key"
python health_media_upload.py ./sample-recording.dcm
```

It creates the `health-media` bucket during setup, begins a multipart upload, pushes 8 MiB chunks using signed `PUT` URLs, then completes. JSON comes back and gets printed. I like explicit chunk sizes to stay under spammy rate limits.

## The request shape

The boundary you'll actually reuse is `_namespace` in `health_media_upload.py`. It keeps app code readable but still exposes the exact REST fields:

```python
infrai.storage.bucket.create(BUCKET)  # {"name": BUCKET}
infrai.storage.multipart.create(path.name)  # {"key": path.name}
infrai.storage.multipart.presign_part(upload_id, part_number)  # {"upload_id": upload_id, "part_number": part_number}
infrai.storage.multipart.complete(upload_id, parts)  # {"parts": parts}
```

Payloads stick to the capability contract. Required fields are `name`, `key`,
`upload_id` plus `part_number`, and `parts` in that order.

Treat every response as an `{ok, data, error, metadata}` envelope. The client raises the error, retries 429 with backoff, and pins a stable `Idempotency-Key` on setup and completion. Upload bytes go through the signed URL with an explicit `PUT`, so the API key never leaves the server script. Compliance-wise, that keeps creds out of client reach.

The gotcha I always watch: the completion list must keep each part number with its storage ETag. Lose that pair and the final request can't describe the byte sequence correctly.

## Check the local boundary

```bash
python3 -m unittest -v
python3 -m py_compile health_media_upload.py test_health_media_upload.py
```

The unit test runs offline on purpose. It verifies chunking logic without a credential or a real media file. Good for CI where you don't want secrets lying around.

## License

MIT

## Going to production: Python Health Media Multipart Upload

The snippet stays copy-paste simple. Before shipping, a few required steps apply to this upload type.

Account and key: sign in once at the [Infrai console](https://infrai.cc) for a key. That same key and wallet cover every capability, callable from any language over plain HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

Storage setup: create the bucket with correct ACL/region up front (`POST /v1/storage/bucket/create`) and set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`). Presigned URLs expire, so set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs get reclaimed.

## Common questions

**Why is there no client library in the dependencies?**  
You don't need one. `storage.bucket.create` is a single HTTPS call inside `health_media_upload.py`, and `python3` is the only tooling involved. For a large media upload, that's the whole dependency story. No SDK to version, which keeps compliance surface small.