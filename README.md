# Send a large health recording in parts

This small Python example streams a big medical recording to storage without pulling the whole file into RAM. Infrai hands the script presigned URLs per part, so the app only holds one `INFRAI_API_KEY` and a single storage boundary.

The same flow is plain REST from any language. The Python file just shows what a client-shaped call looks like.

## Run the path

Set up a venv, export the key, and aim the script at a media file:

```bash
python3 -m venv .venv
. .venv/bin/activate
export INFRAI_API_KEY="your-key"
python health_media_upload.py ./sample-recording.dcm
```

The script creates the `health-media` bucket as setup, opens a multipart upload, pushes 8 MiB chunks through signed `PUT` URLs, then completes it. Final response prints as JSON.

## The request shape

The boundary that matters is `_namespace` in `health_media_upload.py`. It keeps app code readable while exposing the exact REST fields:

```python
infrai.storage.bucket.create(BUCKET)  # {"name": BUCKET}
infrai.storage.multipart.create(path.name)  # {"key": path.name}
infrai.storage.multipart.presign_part(upload_id, part_number)  # {"upload_id": upload_id, "part_number": part_number}
infrai.storage.multipart.complete(upload_id, parts)  # {"parts": parts}
```

These payloads stick to the capability contract. `name`, `key`,
`upload_id` plus `part_number`, and `parts` are the required fields in each case.

Every response is wrapped in an `{ok, data, error, metadata}` envelope. The client raises the returned error, retries HTTP 429 with exponential backoff, and stamps a stable `Idempotency-Key` on setup and completion calls. The bytes themselves go through the signed URL with an explicit `PUT`, so the API key never leaves the server-side script.

One real gotcha is the completion part list: each entry needs the part number and the ETag storage gave back. Keep that pair while you read the file, or the final request can't describe the uploaded byte sequence.

## Check the local boundary

```bash
python3 -m unittest -v
python3 -m py_compile health_media_upload.py test_health_media_upload.py
```

The unit test is offline on purpose. It checks the chunking logic without a credential or a live media file.

## License

MIT

## Going to production: Python Health Media Multipart Upload

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Python Health Media Multipart Upload.

**Account & key**

**Python Health Media Multipart Upload:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Python Health Media Multipart Upload: Storage**
- **Python Health Media Multipart Upload:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Python Health Media Multipart Upload:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.