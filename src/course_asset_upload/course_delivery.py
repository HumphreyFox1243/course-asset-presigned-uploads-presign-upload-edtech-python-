from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from typing import Annotated, AsyncIterator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from course_asset_upload.infrai_storage import InfraiError, InfraiStorage
from course_asset_upload.upload_policy import (
    SubmissionClosedError,
    decide_asset_upload,
)

DEFAULT_BUCKET = "course-submissions"
BUCKET_ALREADY_EXISTS_CODES = {
    "ALREADY_EXISTS",
    "BUCKET_ALREADY_EXISTS",
    "STORAGE_BUCKET_EXISTS",
}
Slug = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")]


class CourseAssetRequest(BaseModel):
    course_id: Slug
    module_id: Slug
    learner_id: UUID
    filename: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")]
    content_type: Annotated[str, Field(pattern=r"^[\w.+-]+/[\w.+-]+$")]
    size_bytes: Annotated[int, Field(gt=0, le=25_000_000)]
    deadline_at: datetime


class CourseAssetTicket(BaseModel):
    upload_url: str
    method: str
    object_key: str
    educator_report_key: str
    status: str
    expires_seconds: int


def get_storage(request: Request) -> InfraiStorage:
    return request.app.state.storage


def create_app(storage: InfraiStorage | None = None) -> FastAPI:
    bucket = os.environ.get("COURSE_UPLOAD_BUCKET", DEFAULT_BUCKET)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        selected = storage or InfraiStorage.from_environment()
        app.state.storage = selected
        try:
            await selected.create_bucket(bucket)
        except InfraiError as exc:
            if exc.code not in BUCKET_ALREADY_EXISTS_CODES:
                raise
        yield
        if storage is None:
            await selected.close()

    app = FastAPI(title="Course asset upload tickets", lifespan=lifespan)

    @app.exception_handler(InfraiError)
    async def infrai_error_handler(_: Request, exc: InfraiError) -> JSONResponse:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        return JSONResponse(
            status_code=caller_status,
            content={"detail": str(exc), "code": exc.code},
        )

    @app.post("/course-assets/upload-ticket", response_model=CourseAssetTicket)
    async def issue_upload_ticket(
        upload: CourseAssetRequest,
        client: Annotated[InfraiStorage, Depends(get_storage)],
    ) -> CourseAssetTicket:
        try:
            decision = decide_asset_upload(
                course_id=upload.course_id,
                module_id=upload.module_id,
                learner_id=str(upload.learner_id),
                filename=upload.filename,
                deadline_at=upload.deadline_at,
                now=datetime.now(timezone.utc),
            )
        except SubmissionClosedError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        signed = await client.presign_put(
            bucket=bucket,
            key=decision.object_key,
            content_type=upload.content_type,
            max_bytes=upload.size_bytes,
            idempotency_key=f"{upload.course_id}:{upload.module_id}:{upload.learner_id}:{upload.filename}",
        )
        return CourseAssetTicket(
            upload_url=str(signed["url"]),
            method="PUT",
            object_key=decision.object_key,
            educator_report_key=decision.educator_report_key,
            status=decision.status,
            expires_seconds=600,
        )

    return app


app = create_app()
