"""Measured cloud observation evaluation over explicitly consented owned images.

The existing local-OCR report stays separate. Labels are used only after a
validated NVIDIA observation has reached the deterministic verifier.
"""

from __future__ import annotations

import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from app.providers.meta import ProviderError
from app.schemas import Task
from app.services.digital_evaluation import (
    DATASET_DIRECTORY,
    case_image,
    manifest_fingerprint,
    summarize_cases,
)
from app.services.digital_verification import verify_screen
from app.services.screen_observation import observe_screen, redact_text

DEFAULT_MODEL = "meta/muse-glimmer-30b"
DEFAULT_HOST = "https://integrate.api.nvidia.com/v1"
MAX_CASES = 20
UNAVAILABLE_CODES = {"connection", "timeout", "upstream_error", "rate_limit", "unavailable", "pending"}
MAX_CONSECUTIVE_UNAVAILABLE = 2
LIMITATIONS = [
    "This is a small controlled CodeLab screenshot challenge, not a representative real-world model benchmark.",
    "Labels were authored by the implementing coding agent before inference and have not been independently reviewed by human annotators.",
    "The same frozen screenshots and reviewed mock workflow are reused from the local OCR challenge. The target is simulated software, not a real extension installation.",
    "NVIDIA-hosted model observations are combined with actual local OCR and deterministic constraints. This is pipeline agreement, not standalone visual-language-model accuracy or tutorial-extraction accuracy.",
    "The observer/verifier never receives the ground-truth classification. Any disagreement or unavailable inference is retained rather than replaced with a requested verdict.",
    "Latency covers local screenshot preparation, local OCR, cloud observation or validated cache lookup, and deterministic verification. It excludes browser capture, user think time, API upload to ReplayLab, and explanation generation.",
    "Cached and fresh cloud observations are identified separately. Overall latency can include cache hits; uncached latency is also reported with its actual sample size.",
    "There is no evidence here of broad application support, calibrated confidence, independent annotation, or physical SAM inference.",
]


def empty_nvidia_report(*, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST) -> dict:
    return {
        "dataset": "ReplayLab CodeLab controlled browser challenge v1 — NVIDIA",
        "provider_mode": "nvidia",
        "evaluation_kind": "nvidia_controlled_browser_pixels",
        "model": model,
        "host": host,
        "live_api_verified": False,
        "measured_at": None,
        "target_size": MAX_CASES,
        "attempted_cases": 0,
        "fresh_observation_count": 0,
        "cached_observation_count": 0,
        "failure_circuit_open": False,
        "stop_reason": None,
        **summarize_cases([]),
        "uncached_latency_ms": summarize_cases([])["latency_ms"],
        "details": [],
        "skipped": [],
        "limitations": LIMITATIONS,
    }


def load_nvidia_report(
    runtime_path: Path | None = None,
    *,
    model: str = DEFAULT_MODEL,
    host: str = DEFAULT_HOST,
    dataset_directory: Path = DATASET_DIRECTORY,
) -> dict:
    """Reading a report never constructs a cloud client or sends media."""
    try:
        fingerprint = manifest_fingerprint((dataset_directory / "cases.json").read_bytes())
    except OSError:
        return empty_nvidia_report(model=model, host=host)
    for path in (runtime_path, dataset_directory / "nvidia-results.json"):
        if path is None or not path.is_file():
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(report, dict):
            continue
        if (
            report.get("provider_mode") != "nvidia"
            or report.get("manifest_sha256") != fingerprint
            or report.get("model") != model
            or report.get("host", "").rstrip("/") != host.rstrip("/")
        ):
            continue
        report["report_source"] = "local_nvidia_rerun" if path == runtime_path else "checked_in_nvidia_measurement"
        return report
    return empty_nvidia_report(model=model, host=host)


def run_nvidia_evaluation(
    screen_provider,
    *,
    cloud_consent: bool = False,
    model: str = DEFAULT_MODEL,
    host: str = DEFAULT_HOST,
    dataset_directory: Path = DATASET_DIRECTORY,
    output_path: Path | None = None,
) -> dict:
    """Send at most 20 frozen repo-owned screenshots after explicit consent.

    Provider transport may retry transient errors according to its documented
    bounded policy. Permanent errors stop immediately; two consecutive unavailable
    responses stop the run. Remaining cases stay unattempted, without predictions.
    """
    if not cloud_consent:
        raise ValueError("Explicit consent is required to send controlled evaluation screenshots to NVIDIA.")
    manifest_bytes = (dataset_directory / "cases.json").read_bytes()
    dataset = json.loads(manifest_bytes)
    cases = dataset["cases"]
    if not cases or len(cases) > MAX_CASES:
        raise ValueError("The NVIDIA challenge must contain between one and twenty controlled cases.")
    task = Task.model_validate(json.loads((dataset_directory / "workflow.json").read_text(encoding="utf-8")))
    by_id = {step.id: step for step in task.steps}
    details, skipped = [], []
    attempted = 0
    stopped_code = None
    stopped_reason = None
    consecutive_unavailable = 0
    for case in cases:
        if stopped_code:
            skipped.append({"id": case.get("id", "unknown"), "attempted": False,
                            "code": stopped_code, "reason": stopped_reason})
            continue
        started = time.perf_counter()
        attempted += 1
        try:
            image_bytes = case_image(case["screenshot"], dataset_directory).read_bytes()
            if hashlib.sha256(image_bytes).hexdigest() != case["screenshot_sha256"]:
                raise ValueError("The screenshot differs from its frozen dataset hash.")
            step = by_id[case["reference_step_id"]]
            observation = observe_screen(image_bytes, "nvidia", screen_provider, cloud_consent=True)
            if (
                observation.provider_mode != "nvidia"
                or observation.provenance.get("live_api_verified") is not True
                or observation.provenance.get("api_response_validated") is not True
            ):
                raise RuntimeError("No validated NVIDIA observation was returned; this case is not scored as live inference.")
            result = verify_screen(step, observation, task, case["completed_step_ids"])
            consecutive_unavailable = 0
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            # Classification is read only after deterministic verification.
            expected = case["expected"]
            provenance = observation.provenance
            details.append({
                "id": case["id"], "title": case["title"], "category": case["category"],
                "expected": expected, "predicted": result.status, "correct": expected == result.status,
                "provider_mode": "nvidia", "model": model,
                "explanation": redact_text(result.explanation),
                "evidence": [redact_text(item) for item in result.evidence],
                "processing_latency_ms": elapsed,
                "cache_hit": provenance.get("cache_hit") is True,
                "model_latency_ms": provenance.get("latency_ms"),
                "response_model": provenance.get("response_model"),
                "screenshot_url": f"/api/evaluation/digital/assets/{case['screenshot']}",
                "screenshot_sha256": case["screenshot_sha256"],
                "reference_step_id": step.id,
                "expected_conditions": [rule.expected for rule in step.screen_rules],
                "observed_conditions": [redact_text(item.text) for item in observation.elements],
                "rule_results": [item.model_dump(mode="json") for item in result.rule_results],
                "interface_version": observation.interface_version, "reason": result.reason,
                "failure_notes": [] if expected == result.status else [
                    f"Ground truth {expected}; pipeline returned {result.status}. Label unchanged."
                ],
            })
        except ProviderError as error:
            skipped.append({"id": case.get("id", "unknown"), "attempted": True,
                            "code": error.code, "reason": redact_text(str(error)),
                            "processing_latency_ms": round((time.perf_counter() - started) * 1000, 2)})
            if error.code in {"authentication", "billing", "forbidden", "not_found", "not_configured", "model_unavailable"}:
                stopped_code = error.code
                stopped_reason = "Not attempted after a permanent provider failure."
            elif error.code in UNAVAILABLE_CODES:
                consecutive_unavailable += 1
                if consecutive_unavailable >= MAX_CONSECUTIVE_UNAVAILABLE:
                    stopped_code = "unavailable_circuit_open"
                    stopped_reason = "Not attempted after two consecutive unavailable NVIDIA requests."
            else:
                consecutive_unavailable = 0
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            consecutive_unavailable = 0
            skipped.append({"id": case.get("id", "unknown"), "attempted": True,
                            "code": "unavailable_evidence", "reason": redact_text(str(error))[:300],
                            "processing_latency_ms": round((time.perf_counter() - started) * 1000, 2)})
    uncached = [item for item in details if not item["cache_hit"]]
    report = {
        **empty_nvidia_report(model=model, host=host),
        "dataset": dataset["name"] + " — NVIDIA",
        "live_api_verified": bool(details),
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": manifest_fingerprint(manifest_bytes),
        "manifest_hash_method": "sha256_utf8_crlf_normalized_to_lf",
        "target_size": len(cases), "attempted_cases": attempted,
        "failure_circuit_open": stopped_code is not None,
        "stop_reason": stopped_code,
        "capture_metadata": dataset.get("capture_metadata", {}),
        "label_provenance": dataset["label_provenance"],
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        **summarize_cases(details),
        "fresh_observation_count": len(uncached),
        "cached_observation_count": len(details) - len(uncached),
        "uncached_latency_ms": summarize_cases(uncached)["latency_ms"],
        "details": details, "skipped": skipped,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(".pending.json")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        temporary.replace(output_path)
    return report
