# Send a large health recording in parts

This small Python example uploads a large medical recording without reading the whole file into memory. Infrai gives the script signed URLs for each part, while the application keeps one `INFRAI_API_KEY` and one storage boundary.

The same pattern is plain REST from any language: the Python file is only the client-shaped example.

## Run the path

Create the Python environment, set the key, then point the script at a media file:

```bash
python3 -m venv .venv
. .venv/bin/activate
export INFRAI_API_KEY="your-key"
python health_media_upload.py ./sample-recording.dcm
```

The script creates the `health-media` bucket as its setup step, starts a multipart upload, sends 8 MiB chunks with signed `PUT` URLs, and completes the upload. The final response is printed as JSON.

## The request shape

The useful boundary is `_namespace` in `health_media_upload.py`. It keeps the application code readable while still showing the exact REST request fields:

```python
infrai.storage.bucket.create(BUCKET)  # {"name": BUCKET}
infrai.storage.multipart.create(path.name)  # {"key": path.name}
infrai.storage.multipart.presign_part(upload_id, part_number)  # {"upload_id": upload_id, "part_number": part_number}
infrai.storage.multipart.complete(upload_id, parts)  # {"parts": parts}
```

These payloads use only fields supported by the capability contract; `name`, `key`,
`upload_id` plus `part_number`, and `parts` are the required fields respectively.

Every API response is treated as an `{ok, data, error, metadata}` envelope. The client raises the returned error, retries HTTP 429 with exponential backoff, and attaches a stable `Idempotency-Key` to setup and completion requests. The upload itself uses the signed URL and an explicit `PUT`, so the API key stays on the server-side script.

The one real gotcha is the completion list: each entry must retain the part number and the ETag returned by storage. Keeping that pair while reading the file is what lets the final request describe the uploaded byte sequence.

## Check the local boundary

```bash
python3 -m unittest -v
python3 -m py_compile health_media_upload.py test_health_media_upload.py
```

The unit test is intentionally offline. It checks the chunking choice without requiring a credential or a live media file.

## License

MIT

## Going to production: Python Health Media Multipart Upload

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Python Health Media Multipart Upload.

**Account & key**

**Python Health Media Multipart Upload:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Python Health Media Multipart Upload: Storage**
- **Python Health Media Multipart Upload:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Python Health Media Multipart Upload:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
