from fastapi.testclient import TestClient
import pytest

from course_asset_upload.course_delivery import create_app
from course_asset_upload.infrai_storage import InfraiError


class FakeStorage:
    def __init__(self, create_error: InfraiError | None = None) -> None:
        self.create_error = create_error
        self.created_bucket: str | None = None

    async def create_bucket(self, name: str) -> dict:
        self.created_bucket = name
        if self.create_error:
            raise self.create_error
        return {}


def test_startup_uses_configured_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COURSE_UPLOAD_BUCKET", "course-submissions-test")
    storage = FakeStorage()

    with TestClient(create_app(storage=storage)):
        pass

    assert storage.created_bucket == "course-submissions-test"


def test_startup_accepts_existing_bucket() -> None:
    storage = FakeStorage(
        InfraiError("STORAGE_BUCKET_EXISTS", {"message": "already exists"}, 409)
    )

    with TestClient(create_app(storage=storage)):
        pass


def test_startup_does_not_hide_other_conflicts() -> None:
    storage = FakeStorage(
        InfraiError("NAME_RESERVED", {"message": "reserved"}, 409)
    )

    with pytest.raises(InfraiError, match="reserved"):
        with TestClient(create_app(storage=storage)):
            pass
