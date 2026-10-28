"""Replay the frozen controlled screenshot dataset using real local OCR."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.services.digital_evaluation import run_digital_evaluation  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "apps/api/data/evaluation/digital-latest.json")
    args = parser.parse_args()
    report = run_digital_evaluation(output_path=args.output)
    print(json.dumps({key: report[key] for key in (
        "dataset", "sample_size", "correct", "accuracy", "decisive_accuracy", "false_certainty_rate",
        "uncertainty_recall", "decisive_misclassifications", "latency_ms", "confusion_matrix", "skipped"
    )}, indent=2))
    if report["skipped"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
