from typing import Dict, Optional
from app.models.extraction_models import ExtractionJobStatus, ExtractionResult

class JobService:
    def __init__(self):
        self._jobs: Dict[str, ExtractionJobStatus] = {}
        self._results: Dict[str, ExtractionResult] = {}

    def create_job(self, job_id: str, filename: str, file_type: str) -> ExtractionJobStatus:
        status = ExtractionJobStatus(
            job_id=job_id,
            filename=filename,
            file_type=file_type,
            status="uploaded",
            stage="uploading",
            progress=0
        )
        self._jobs[job_id] = status
        return status

    def update_job_status(
        self,
        job_id: str,
        status: str,
        stage: str,
        progress: int,
        current_page: Optional[int] = None,
        total_pages: Optional[int] = None,
        stage_message: Optional[str] = None,
        error: Optional[str] = None
    ):
        if job_id in self._jobs:
            self._jobs[job_id].status = status
            self._jobs[job_id].stage = stage
            self._jobs[job_id].progress = progress
            if current_page is not None:
                self._jobs[job_id].current_page = current_page
            if total_pages is not None:
                self._jobs[job_id].total_pages = total_pages
            if stage_message is not None:
                self._jobs[job_id].stage_message = stage_message
            if error:
                self._jobs[job_id].error = error

    def get_job_status(self, job_id: str) -> Optional[ExtractionJobStatus]:
        return self._jobs.get(job_id)

    def save_result(self, job_id: str, result: ExtractionResult):
        self._results[job_id] = result

    def get_result(self, job_id: str) -> Optional[ExtractionResult]:
        return self._results.get(job_id)

job_service = JobService()
