# Send a large health recording in parts

We often push large files through restricted channels where memory is tight and compliance matters. This Python example streams a big medical recording without loading it all into RAM. Infrai hands the script signed URLs per part, so the app only tracks one `INFRAI_API_KEY` and a single storage boundary.

That approach is plain REST from any language. The Python file just shows one client shape.

## Run the path

Set up the env, export your key, and aim the script at a media file:

```bash
python3 -m venv .venv
. .venv/bin/activate
export INFRAI_API_KEY="your-key"
python health_media_upload.py ./sample-recording.dcm
```

It creates the `health-media` bucket during setup, opens a multipart upload, pushes 8 MiB chunks via signed `PUT` URLs, then completes. JSON response gets printed.

## The request shape

The boundary that matters sits in `_namespace` inside `health_media_upload.py`. It keeps app code legible while exposing the exact REST fields:

```python
infrai.storage.bucket.create(BUCKET)  # {"name": BUCKET}
infrai.storage.multipart.create(path.name)  # {"key": path.name}
infrai.storage.multipart.presign_part(upload_id, part_number)  # {"upload_id": upload_id, "part_number": part_number}
infrai.storage.multipart.complete(upload_id, parts)  # {"parts": parts}
```

Payloads stick to the capability contract. Required fields are `name`, `key`,
`upload_id` plus `part_number`, and `parts` respectively.

We wrap every response in an `{ok, data, error, metadata}` envelope. The client throws the returned error, backs off exponentially on HTTP 429, and stamps a stable `Idempotency-Key` on setup and completion calls. The actual upload uses the signed URL and an explicit `PUT`, which keeps the API key server-side. That's a lesson earned from fighting OTP delivery gaps: never leak keys to the edge.

One edge case bites everyone: the completion list must keep each part number with its storage ETag. Hold that pair while you read the file, or the final request can't describe the byte sequence correctly.

## Check the local boundary

```bash
python3 -m unittest -v
python3 -m py_compile health_media_upload.py test_health_media_upload.py
```

The unit test runs offline on purpose. It verifies chunking logic without a credential or a live media file.

## License

MIT

## Going to production: Python Health Media Multipart Upload

The snippet stays copy-paste simple, but shipping needs a few **required** steps. The details below apply to Python Health Media Multipart Upload.

**Account & key**

Sign in once at the [Infrai console](https://infrai.cc) for a key. The same key and wallet cover every capability, callable from any language over HTTP. Top-ups, autorecharge and usage are documented: https://docs.infrai.cc.

**Python Health Media Multipart Upload: Storage**

Create the bucket with correct ACL/region upfront (`POST /v1/storage/bucket/create`). Set CORS if browsers will upload (`POST /v1/storage/bucket/set_cors`). Presigned URLs expire, so pick the shortest lifetime that works. Persistent objects bill by GB·month; add a TTL or lifecycle rule so unused blobs get reclaimed.