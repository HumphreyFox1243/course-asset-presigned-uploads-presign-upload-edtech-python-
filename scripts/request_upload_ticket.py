import json
import os
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen


payload = {
    "course_id": "biology-101",
    "module_id": "cell-lab",
    "learner_id": "7e135fe5-d864-4b9a-b79d-3c0ecde4cbe2",
    "filename": "microscope.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 2_000_000,
    "deadline_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
}

request = Request(
    os.environ.get(
        "COURSE_UPLOAD_SERVICE_URL",
        "http://127.0.0.1:8000/course-assets/upload-ticket",
    ),
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urlopen(request) as response:
    print(json.dumps(json.load(response), indent=2))

