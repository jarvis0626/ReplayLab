"""Evaluate consented repo-owned screenshots with actual NVIDIA observations."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.core.config import Settings
from app.services.nvidia_evaluation import run_nvidia_evaluation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--consent-controlled-screenshots", action="store_true",
                        help="Consent to send only the frozen repo-owned controlled screenshots to NVIDIA.")
    parser.add_argument("--output", type=Path, default=ROOT / "apps/api/data/evaluation/nvidia-latest.json")
    parser.add_argument("--timeout-seconds", type=float, default=None,
                        help="Override the per-request timeout for this bounded run (5–180 seconds).")
    args = parser.parse_args()
    if args.timeout_seconds is not None and not 5 <= args.timeout_seconds <= 180:
        parser.error("--timeout-seconds must be between 5 and 180.")
    if not args.consent_controlled_screenshots:
        parser.error("Pass --consent-controlled-screenshots to authorize this bounded cloud evaluation.")
    # Resolve the existing local env location explicitly without printing values.
    settings = Settings(_env_file=ROOT / "apps/api/.env")
    key = getattr(settings, "nvidia_api_key", "") or os.environ.get("NVIDIA_API_KEY", "")
    if not key:
        parser.error("NVIDIA_API_KEY is not configured on the server. No screenshots were sent.")
    from app.providers.nvidia import NvidiaProvider, NvidiaScreenProvider

    provider = NvidiaProvider(
        key, settings.data_dir / "inference-cache", base_url=settings.nvidia_base_url, model=settings.nvidia_model,
        timeout_seconds=args.timeout_seconds if args.timeout_seconds is not None else getattr(settings, "nvidia_timeout_seconds", 45),
        max_tokens=getattr(settings, "nvidia_max_tokens", 4096),
        reasoning_effort=getattr(settings, "nvidia_reasoning_effort", "low"),
    )
    report = run_nvidia_evaluation(
        NvidiaScreenProvider(provider), cloud_consent=True, model=settings.nvidia_model,
        host=settings.nvidia_base_url, output_path=args.output,
    )
    print(json.dumps({name: report[name] for name in (
        "dataset", "provider_mode", "model", "host", "sample_size", "target_size", "attempted_cases",
        "failure_circuit_open", "stop_reason", "correct", "accuracy",
        "decisive_accuracy", "false_certainty_rate", "uncertainty_recall", "decisive_misclassifications",
        "latency_ms", "uncached_latency_ms", "fresh_observation_count", "cached_observation_count",
        "confusion_matrix", "skipped",
    )}, indent=2))
    if report["skipped"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
