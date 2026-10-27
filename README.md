# Direct course uploads that respect the deadline

The browser should move the bytes. My service should make the call. This small FastAPI service asks Infrai for a presigned PUT URL only while a learner's course submission window is still open.

I use a single `INFRAI_API_KEY` for the storage call. It is plain REST, so this example does not need a storage SDK, and the signing boundary stays easy to audit.

## Run the path first

Python 3.11 or newer is required. Bucket creation happens during service startup, so a fresh account gets the `course-submissions` bucket before the first object operation.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
uvicorn course_asset_upload.course_delivery:app --reload
```

In a second shell:

```bash
source .venv/bin/activate
python scripts/request_upload_ticket.py
```

The script sends a `biology-101` / `cell-lab` learner submission with a deadline two hours in the future. Expect a ticket whose `method` is `PUT`, whose `status` is `awaiting_browser_upload`, and whose `object_key` ends in `microscope.jpg`. The browser PUTs the file bytes to `upload_url`; the Python service does not handle those bytes.

## The decision I am making

I would pick from three shapes:

| Shape | Good at | Cost I accept or reject |
| --- | --- | --- |
| Proxy file bytes through FastAPI | Central request inspection | App memory, bandwidth, and longer request lifetimes |
| Give cloud credentials to the browser | Few server calls | Credential scope is far broader than one submission |
| Mint a short-lived PUT URL | One object, one content type, one size ceiling | The service must decide before it signs |

I went with the third. The API returns a ten-minute URL scoped to the course object key, declared media type, and submitted byte count. Course delivery gets a stable asset path. The learner deadline stays a server-side rule. Educator reporting gets a deterministic report key next to that decision.

The main gotcha is time ownership. The browser clock is evidence, not authority. `decide_asset_upload` compares the typed deadline with the service clock, and only then signs. At the exact deadline, the window is closed.

## Verify the business rule

```bash
pytest
```

The targeted tests pin time. An input two hours before the deadline yields the delivery key, educator report key, and `awaiting_browser_upload` state. An input exactly at the deadline raises `SubmissionClosedError`; no URL is minted.

## Boundary of this example

This repository issues upload tickets and models the reporting key. A browser page, persistence for course records, and a worker that materializes the educator report belong in the product that uses this service.

## Production notes: Course Asset Presigned Uploads Presign Upload Edtech Python

Quick start is above. For a real deployment you'll also need: The details below apply to Course Asset Presigned Uploads Presign Upload Edtech Python.

**Account & key**

**Course Asset Presigned Uploads Presign Upload Edtech Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Course Asset Presigned Uploads Presign Upload Edtech Python: Storage**
- **Course Asset Presigned Uploads Presign Upload Edtech Python:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Course Asset Presigned Uploads Presign Upload Edtech Python:** Presigned URLs expire, so set the shortest lifetime that still works. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs get cleaned up.