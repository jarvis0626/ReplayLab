"""Repeatable OCR evaluation over a frozen, labeled controlled browser dataset.

Labels are read only after prediction. They are never passed to the observer or
verifier. This measures the controlled screenshot pipeline, not Meta accuracy.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import Task
from app.services.digital_verification import verify_screen
from app.services.screen_observation import clear_screen_cache, observe_screen

DATASET_DIRECTORY = Path(__file__).resolve().parents[4] / "demo" / "evaluation" / "digital"
STATUSES = ("pass", "fail", "uncertain")
LIMITATIONS = [
    "Twenty controlled CodeLab screenshots are a small authored challenge set, not a representative real-world benchmark.",
    "Labels were fixed by the implementing coding agent before inference; they have not been independently reviewed by human annotators.",
    "The CodeLab target is an interactive software simulation. No third-party extension is installed.",
    "Real local OCR reads captured browser pixels; workflow rules use the reviewed mock demonstration template. No live Meta inference is measured.",
    "These cases are stored separately from development observation fixtures, but share CodeLab and its expected labels. This is not a held-out application or blinded evaluation.",
    "Latency covers uncached screenshot decode, local OCR, deterministic verification, and result construction; it excludes browser capture, transport, and cloud calls. The first sample can include OCR initialization.",
    "Ambiguous and version-difference cases deliberately exercise abstention. A matching small-set score does not establish broad accuracy or calibrated confidence.",
]


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def summarize_cases(details: list[dict]) -> dict:
    """Compute metrics with explicit denominators and nullable empty metrics."""
    confusion = {actual: {predicted: 0 for predicted in STATUSES} for actual in STATUSES}
    for item in details:
        confusion[item["expected"]][item["predicted"]] += 1
    decisive = [item for item in details if item["predicted"] in {"pass", "fail"}]
    uncertain = [item for item in details if item["expected"] == "uncertain"]
    false_certainty = sum(item["predicted"] != "uncertain" for item in uncertain)
    swaps = sum(
        item["expected"] in {"pass", "fail"}
        and item["predicted"] in {"pass", "fail"}
        and item["expected"] != item["predicted"]
        for item in details
    )
    latencies = sorted(item["processing_latency_ms"] for item in details)
    correct = sum(item["correct"] for item in details)
    return {
        "sample_size": len(details),
        "correct": correct,
        "accuracy": _ratio(correct, len(details)),
        "decisive_accuracy": _ratio(sum(item["correct"] for item in decisive), len(decisive)),
        "decisive_predictions": len(decisive),
        "false_certainty_rate": _ratio(false_certainty, len(uncertain)),
        "false_certainty_count": false_certainty,
        "uncertain_ground_truth_count": len(uncertain),
        "uncertainty_recall": _ratio(sum(item["predicted"] == "uncertain" for item in uncertain), len(uncertain)),
        "decisive_misclassifications": swaps,
        "latency_ms": {
            "sample_size": len(latencies),
            "median": round(statistics.median(latencies), 2) if latencies else None,
            "p95": latencies[math.ceil(len(latencies) * 0.95) - 1] if latencies else None,
            "min": latencies[0] if latencies else None,
            "max": latencies[-1] if latencies else None,
        },
        "confusion_matrix": confusion,
        "confusion_matrix_axes": {"rows": "expected", "columns": "predicted"},
        "metric_definitions": {
            "accuracy": "Correct three-class verdicts / all completed cases.",
            "decisive_accuracy": "Correct PASS or FAIL predictions / all PASS or FAIL predictions, including predictions on UNCERTAIN ground truth.",
            "false_certainty_rate": "PASS or FAIL predictions on UNCERTAIN ground truth / all UNCERTAIN ground-truth cases.",
            "uncertainty_recall": "UNCERTAIN predictions on UNCERTAIN ground truth / all UNCERTAIN ground-truth cases.",
            "decisive_misclassifications": "PASS ground truth predicted FAIL plus FAIL ground truth predicted PASS; excludes abstentions and uncertain ground truth.",
            "p95": "Nearest-rank 95th percentile of completed-case processing latency.",
        },
    }


def empty_report() -> dict:
    return {
        "dataset": "ReplayLab CodeLab controlled browser challenge v1",
        "provider_mode": "local_ocr",
        "evaluation_kind": "controlled_browser_pixels",
        "measured_at": None,
        "target_size": 20,
        **summarize_cases([]),
        "details": [],
        "skipped": [],
        "limitations": LIMITATIONS,
    }


def manifest_fingerprint(payload: bytes) -> str:
    """Hash manifest text identically before and after Git newline conversion.

    Screenshot integrity checks intentionally keep hashing the exact binary
    bytes. Only the UTF-8 JSON manifest normalizes Windows CRLF to LF.
    """
    return hashlib.sha256(payload.replace(b"\r\n", b"\n")).hexdigest()


def load_report(runtime_path: Path | None = None) -> dict:
    try:
        manifest_hash = manifest_fingerprint((DATASET_DIRECTORY / "cases.json").read_bytes())
    except OSError:
        report = empty_report()
        report["limitations"] = [*LIMITATIONS, "The screenshot dataset is unavailable; no current measurement is shown."]
        return report
    paths = [runtime_path, DATASET_DIRECTORY / "baseline-results.json"]
    for path in paths:
        if path and path.is_file():
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if report.get("manifest_sha256") != manifest_hash:
                continue
            report["report_source"] = "local_rerun" if path == runtime_path else "checked_in_measurement"
            return report
    report = empty_report()
    report["limitations"] = [*LIMITATIONS, "No measurement matches the current case manifest; run the local evaluation."]
    return report


def case_image(filename: str, directory: Path = DATASET_DIRECTORY) -> Path:
    if not re.fullmatch(r"case-[a-z0-9-]+\.png", filename):
        raise ValueError("Invalid evaluation image name.")
    path = directory / "screenshots" / filename
    if not path.is_file():
        raise FileNotFoundError("The evaluation screenshot is unavailable.")
    return path


def run_digital_evaluation(
    *, dataset_directory: Path = DATASET_DIRECTORY, output_path: Path | None = None
) -> dict:
    """Evaluate only controlled repo-owned screenshots; never accept user images."""
    manifest_bytes = (dataset_directory / "cases.json").read_bytes()
    dataset = json.loads(manifest_bytes)
    task = Task.model_validate(json.loads((dataset_directory / "workflow.json").read_text(encoding="utf-8")))
    by_id = {step.id: step for step in task.steps}
    details, skipped = [], []
    for case in dataset["cases"]:
        clear_screen_cache()
        started = time.perf_counter()
        try:
            image_path = case_image(case["screenshot"], dataset_directory)
            image_bytes = image_path.read_bytes()
            if hashlib.sha256(image_bytes).hexdigest() != case["screenshot_sha256"]:
                raise ValueError("The screenshot differs from its frozen dataset hash.")
            step = by_id[case["reference_step_id"]]
            observation = observe_screen(image_bytes, mode="mock")
            if not observation.provenance.get("real_ocr"):
                raise RuntimeError("Real local OCR was unavailable; this case was not evaluated.")
            result = verify_screen(step, observation, task, case["completed_step_ids"])
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            # Ground truth is used for scoring only after the verdict exists.
            expected = case["expected"]
            details.append({
                "id": case["id"],
                "title": case["title"],
                "category": case["category"],
                "expected": expected,
                "predicted": result.status,
                "correct": expected == result.status,
                "explanation": result.explanation,
                "evidence": result.evidence,
                "processing_latency_ms": elapsed,
                "screenshot_url": f"/api/evaluation/digital/assets/{case['screenshot']}",
                "screenshot_sha256": case["screenshot_sha256"],
                "reference_step_id": step.id,
                "expected_conditions": [rule.expected for rule in step.screen_rules],
                "observed_conditions": [item.text for item in observation.elements],
                "rule_results": [item.model_dump(mode="json") for item in result.rule_results],
                "interface_version": observation.interface_version,
                "reason": result.reason,
                "failure_notes": [] if expected == result.status else [
                    f"Ground truth {expected}; pipeline returned {result.status}. Retained without changing the label."
                ],
            })
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            skipped.append({"id": case.get("id", "unknown"), "reason": str(error)[:300]})
    report = {
        **empty_report(),
        "dataset": dataset["name"],
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": manifest_fingerprint(manifest_bytes),
        "manifest_hash_method": "sha256_utf8_crlf_normalized_to_lf",
        "target_size": len(dataset["cases"]),
        "capture_metadata": dataset.get("capture_metadata", {}),
        "label_provenance": dataset["label_provenance"],
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        **summarize_cases(details),
        "details": details,
        "skipped": skipped,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(".pending.json")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        temporary.replace(output_path)
    return report
