"""Read and replay a small controlled digital screenshot evaluation."""

import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from app.services.digital_evaluation import case_image, load_report, run_digital_evaluation
from app.providers.meta import ProviderError
from app.services.nvidia_evaluation import (
    DEFAULT_HOST,
    DEFAULT_MODEL,
    load_nvidia_report,
    run_nvidia_evaluation,
)


class NvidiaEvaluationConsent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cloud_consent: bool = False


def register_evaluation_routes(api: FastAPI):
    output = api.state.settings.data_dir.resolve() / "evaluation" / "digital-latest.json"
    run_lock = threading.Lock()
    nvidia_output = api.state.settings.data_dir.resolve() / "evaluation" / "nvidia-latest.json"
    nvidia_run_lock = threading.Lock()

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

    @api.get("/api/evaluation/nvidia")
    def nvidia_evaluation_report():
        settings = api.state.settings
        return load_nvidia_report(
            nvidia_output,
            model=getattr(settings, "nvidia_model", DEFAULT_MODEL),
            host=getattr(settings, "nvidia_base_url", DEFAULT_HOST),
        )

    @api.post("/api/evaluation/nvidia/run")
    async def nvidia_evaluation_run(body: NvidiaEvaluationConsent):
        if not body.cloud_consent:
            raise HTTPException(422, "Explicit consent is required to send the controlled evaluation screenshots to NVIDIA.")
        settings = api.state.settings
        key = getattr(settings, "nvidia_api_key", "")
        if not key:
            raise HTTPException(503, "Configure NVIDIA_API_KEY on the server before running the live evaluation.")
        if not nvidia_run_lock.acquire(blocking=False):
            raise HTTPException(409, "The NVIDIA screenshot evaluation is already running.")
        try:
            from app.providers.nvidia import NvidiaProvider, NvidiaScreenProvider

            model = getattr(settings, "nvidia_model", DEFAULT_MODEL)
            host = getattr(settings, "nvidia_base_url", DEFAULT_HOST)
            provider = NvidiaProvider(
                key, settings.data_dir.resolve() / "inference-cache", base_url=host, model=model,
                timeout_seconds=getattr(settings, "nvidia_timeout_seconds", 45),
                max_tokens=getattr(settings, "nvidia_max_tokens", 4096),
                reasoning_effort=getattr(settings, "nvidia_reasoning_effort", "low"),
            )
            return await run_in_threadpool(
                run_nvidia_evaluation, NvidiaScreenProvider(provider), cloud_consent=True,
                model=model, host=host, output_path=nvidia_output,
            )
        except ProviderError as error:
            raise HTTPException(502, str(error)) from None
        except (OSError, ValueError) as error:
            raise HTTPException(503, "The controlled NVIDIA evaluation dataset is unavailable or invalid.") from error
        finally:
            nvidia_run_lock.release()
