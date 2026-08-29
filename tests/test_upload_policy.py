from datetime import datetime, timedelta, timezone

import pytest

from course_asset_upload.upload_policy import (
    SubmissionClosedError,
    decide_asset_upload,
)


def test_open_deadline_routes_asset_for_delivery_and_reporting() -> None:
    now = datetime(2026, 8, 14, 9, 0, tzinfo=timezone.utc)

    decision = decide_asset_upload(
        course_id="biology-101",
        module_id="cell-lab",
        learner_id="7e135fe5-d864-4b9a-b79d-3c0ecde4cbe2",
        filename="microscope.jpg",
        deadline_at=now + timedelta(hours=2),
        now=now,
    )

    assert decision.status == "awaiting_browser_upload"
    assert decision.object_key == (
        "courses/biology-101/modules/cell-lab/learners/"
        "7e135fe5-d864-4b9a-b79d-3c0ecde4cbe2/microscope.jpg"
    )
    assert decision.educator_report_key == (
        "courses/biology-101/reports/cell-lab.json"
    )


def test_closed_deadline_refuses_a_new_upload_ticket() -> None:
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(SubmissionClosedError, match="window is closed"):
        decide_asset_upload(
            course_id="biology-101",
            module_id="cell-lab",
            learner_id="7e135fe5-d864-4b9a-b79d-3c0ecde4cbe2",
            filename="late.jpg",
            deadline_at=now,
            now=now,
        )

