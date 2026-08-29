from dataclasses import dataclass
from datetime import datetime


class SubmissionClosedError(ValueError):
    """Raised when a learner's upload window has closed."""


@dataclass(frozen=True)
class AssetUploadDecision:
    object_key: str
    educator_report_key: str
    status: str


def decide_asset_upload(
    *,
    course_id: str,
    module_id: str,
    learner_id: str,
    filename: str,
    deadline_at: datetime,
    now: datetime,
) -> AssetUploadDecision:
    if now >= deadline_at:
        raise SubmissionClosedError("The learner submission window is closed.")

    object_key = (
        f"courses/{course_id}/modules/{module_id}/"
        f"learners/{learner_id}/{filename}"
    )
    return AssetUploadDecision(
        object_key=object_key,
        educator_report_key=f"courses/{course_id}/reports/{module_id}.json",
        status="awaiting_browser_upload",
    )

