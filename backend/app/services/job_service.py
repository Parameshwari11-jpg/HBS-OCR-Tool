import os
import json
import logging
from typing import Dict, Optional
from app.models.extraction_models import ExtractionJobStatus, ExtractionResult
from app.utils.file_utils import get_job_temp_dir

logger = logging.getLogger("job_service")

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
        self._persist_status(job_id, status)
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
        if job_id not in self._jobs:
            self._load_status_from_disk(job_id)

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
            self._persist_status(job_id, self._jobs[job_id])

    def get_job_status(self, job_id: str) -> Optional[ExtractionJobStatus]:
        if job_id in self._jobs:
            return self._jobs[job_id]
        return self._load_status_from_disk(job_id)

    def save_result(self, job_id: str, result: ExtractionResult):
        self._results[job_id] = result
        self._persist_result(job_id, result)

    def get_result(self, job_id: str) -> Optional[ExtractionResult]:
        if job_id in self._results:
            return self._results[job_id]
        return self._load_result_from_disk(job_id)

    def find_latest_result(self, filename: Optional[str] = None) -> Optional[ExtractionResult]:
        def normalize_name(name: str) -> str:
            s = os.path.splitext(os.path.basename(name).lower())[0]
            for suffix in ["_extracted", " extracted", "-extracted", ".txt", ".json", ".docx", ".pdf"]:
                s = s.replace(suffix, "")
            return "".join(c for c in s if c.isalnum())

        norm_q = normalize_name(filename) if filename else ""

        # 1. Search in-memory results (most recent first)
        for jid in reversed(list(self._results.keys())):
            res = self._results[jid]
            if not filename or not norm_q:
                return res
            norm_doc = normalize_name(res.filename)
            if norm_q in norm_doc or norm_doc in norm_q:
                return res

        # 2. Search disk temp folders ordered by modification time (most recent first)
        latest_any_result = None
        try:
            from app.utils.file_utils import get_upload_dir
            temp_base = get_upload_dir().parent / "temp"
            if temp_base.exists():
                subdirs = []
                for d in temp_base.iterdir():
                    if d.is_dir():
                        try:
                            subdirs.append((d.stat().st_mtime, d))
                        except Exception:
                            pass
                subdirs.sort(key=lambda x: x[0], reverse=True)

                for _, d in subdirs:
                    res_path = d / "result.json"
                    if res_path.exists():
                        try:
                            with open(res_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            fn = data.get("filename", "")
                            res_obj = ExtractionResult.model_validate(data)
                            if latest_any_result is None:
                                latest_any_result = res_obj

                            if not filename or not norm_q:
                                return res_obj
                            norm_doc = normalize_name(fn)
                            if norm_q in norm_doc or norm_doc in norm_q:
                                return res_obj
                        except Exception as e:
                            logger.debug(f"Error reading result in {d}: {e}")
        except Exception as ex:
            logger.debug(f"find_latest_result error: {ex}")

        # If specific filename query was requested but not matched, do not fallback to an unrelated file
        if filename and norm_q:
            return None

        return latest_any_result

    def _persist_status(self, job_id: str, status: ExtractionJobStatus):
        try:
            temp_dir = get_job_temp_dir(job_id)
            status_path = temp_dir / "status.json"
            with open(status_path, "w", encoding="utf-8") as f:
                f.write(status.model_dump_json(indent=2))
        except Exception as e:
            logger.debug(f"Could not persist status to disk for {job_id}: {e}")

    def _load_status_from_disk(self, job_id: str) -> Optional[ExtractionJobStatus]:
        try:
            temp_dir = get_job_temp_dir(job_id)
            status_path = temp_dir / "status.json"
            if status_path.exists():
                with open(status_path, "r", encoding="utf-8") as f:
                    st = ExtractionJobStatus.model_validate_json(f.read())
                    self._jobs[job_id] = st
                    return st
            # If result.json exists, reconstruct completed status
            result_path = temp_dir / "result.json"
            if result_path.exists():
                with open(result_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    total_pages = len(data.get("pages", []))
                    st = ExtractionJobStatus(
                        job_id=job_id,
                        filename=data.get("filename", "document"),
                        file_type=data.get("file_type", "pdf"),
                        status="completed",
                        stage="completed",
                        progress=100,
                        current_page=total_pages,
                        total_pages=total_pages,
                        stage_message=f"Successfully extracted {total_pages} pages!"
                    )
                    self._jobs[job_id] = st
                    return st
        except Exception as e:
            logger.debug(f"Could not load status from disk for {job_id}: {e}")
        return None

    def _persist_result(self, job_id: str, result: ExtractionResult):
        try:
            temp_dir = get_job_temp_dir(job_id)
            result_path = temp_dir / "result.json"
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))
        except Exception as e:
            logger.warning(f"Could not persist result to disk for {job_id}: {e}")

    def _load_result_from_disk(self, job_id: str) -> Optional[ExtractionResult]:
        try:
            temp_dir = get_job_temp_dir(job_id)
            result_path = temp_dir / "result.json"
            if result_path.exists():
                with open(result_path, "r", encoding="utf-8") as f:
                    res = ExtractionResult.model_validate_json(f.read())
                    self._results[job_id] = res
                    return res
        except Exception as e:
            logger.warning(f"Could not load result from disk for {job_id}: {e}")
        return None

job_service = JobService()
