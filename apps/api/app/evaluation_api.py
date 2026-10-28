"""Read and replay a small controlled digital screenshot evaluation."""

import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.services.digital_evaluation import case_image, load_report, run_digital_evaluation


def register_evaluation_routes(api: FastAPI):
    output = api.state.settings.data_dir.resolve() / "evaluation" / "digital-latest.json"
    run_lock = threading.Lock()

    @api.get("/api/evaluation/digital")
    def digital_evaluation_report():
        return load_report(output)

    @api.post("/api/evaluation/digital/run")
    async def digital_evaluation_run():
        if not run_lock.acquire(blocking=False):
            raise HTTPException(409, "The local screenshot evaluation is already running.")
        try:
            return await run_in_threadpool(run_digital_evaluation, output_path=output)
        except (OSError, ValueError) as error:
            raise HTTPException(503, "The controlled evaluation dataset is unavailable or invalid.") from error
        finally:
            run_lock.release()

    @api.get("/api/evaluation/digital/assets/{filename}")
    def digital_evaluation_asset(filename: str):
        try:
            return FileResponse(case_image(filename), media_type="image/png")
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Evaluation screenshot not found.") from None
