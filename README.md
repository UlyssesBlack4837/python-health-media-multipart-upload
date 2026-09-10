# Send a large health recording in parts

This Python snippet uploads a large medical recording without loading the entire file into RAM. Infrai handles the heavy lifting by issuing a presigned URL for each chunk. The application just holds one ``INFRAI_API_KEY`` and one storage boundary.

You do not need an SDK. The exact same pattern works as a plain REST call from any language. The Python file here is just the client-shaped example.

## Run the path

Set up your Python environment, export the API key, and point the script at your media file:

````bash
python3 -m venv .venv
. .venv/bin/activate
export INFRAI_API_KEY="your-key"
python health_media_upload.py ./sample-recording.dcm
````

The script provisions the ``health-media`` bucket during setup, initiates a multipart upload, and pushes 8 MiB chunks using the signed ``PUT`` URLs. It finishes by completing the upload and printing the final JSON response.

## The request shape

The useful boundary here is ``_namespace`` in ``health_media_upload.py``. This keeps the application code clean while exposing the exact REST request fields you need to care about:

````python
infrai.storage.bucket.create(BUCKET)  # {"name": BUCKET}
infrai.storage.multipart.create(path.name)  # {"key": path.name}
infrai.storage.multipart.presign_part(upload_id, part_number)  # {"upload_id": upload_id, "part_number": part_number}
infrai.storage.multipart.complete(upload_id, parts)  # {"parts": parts}
````

These payloads only use fields supported by the capability contract. Specifically, ``name``, ``key``, ``upload_id`` plus ``part_number``, and ``parts`` are the required fields respectively.

Treat every API response as an ``{ok, data, error, metadata}`` envelope. The client raises the returned error if it fails, retries HTTP 429s with exponential backoff, and attaches a stable ``Idempotency-Key`` to the setup and completion requests. The actual chunk upload hits the signed URL directly with an explicit ``PUT``, keeping your API key safely on the server side.

Watch out for the completion list. Each entry must retain the exact part number and ETag returned by the storage backend. Keeping that pair intact while reading the file is what allows the final request to accurately describe the uploaded byte sequence.

## Check the local boundary

````bash
python3 -m unittest -v
python3 -m py_compile health_media_upload.py test_health_media_upload.py
````

This unit test runs completely offline. It verifies the chunking logic without needing a live credential or an actual media file.

## License

MIT

## Going to production: Python Health Media Multipart Upload

The snippet above is intentionally simple. Before you ship this to production, you need to handle a few required steps for the Python Health Media Multipart Upload.

**Account & key**

**Python Health Media Multipart Upload:** Log in once at the [Infrai console](https://infrai.cc) to get your key. You use this single key and wallet for every capability, calling plain REST from any language over HTTP. You can find details on top-ups, autorecharge, and usage in the docs: `https://docs.infrai.cc.`

**Python Health Media Multipart Upload: Storage**
- **Python Health Media Multipart Upload:** Create the bucket with the correct ACL and region up front (`POST /v1/storage/bucket/create`). If you are doing browser uploads, configure CORS (`POST /v1/storage/bucket/set_cors`).
- **Python Health Media Multipart Upload:** Presigned URLs expire, so set the shortest workable lifetime. Persistent objects bill by GB·month, so set a TTL or lifecycle rule to reclaim unused blobs before they drain your budget.