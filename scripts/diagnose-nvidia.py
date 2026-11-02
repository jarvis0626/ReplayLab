"""Check ReplayLab's NVIDIA text path before optionally testing an owned image."""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))


def main():
    from app.core.config import Settings
    from app.providers.meta import ProviderError
    from app.providers.nvidia import NvidiaProvider, NvidiaScreenProvider
    from app.services.screen_observation import observe_screen

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--consent-controlled-screenshot", action="store_true",
                        help="After a successful text call, send the repo-owned synthetic CodeLab screenshot.")
    args = parser.parse_args()
    if not 5 <= args.timeout_seconds <= 180:
        parser.error("Timeout must be between 5 and 180 seconds.")
    settings = Settings(_env_file=ROOT / "apps" / "api" / ".env")
    if not settings.nvidia_api_key:
        raise SystemExit("Run scripts/configure-nvidia.py to enter a server key with hidden input first.")
    provider = NvidiaProvider(settings.nvidia_api_key, settings.data_dir / "inference-cache",
        base_url=settings.nvidia_base_url, model=settings.nvidia_model,
        timeout_seconds=args.timeout_seconds, max_tokens=settings.nvidia_max_tokens,
        reasoning_effort=settings.nvidia_reasoning_effort)
    report = {"checked_at": datetime.now(UTC).isoformat(), "host": settings.nvidia_base_url,
              "configured_model": settings.nvidia_model, "text_verified": False,
              "image_verified": False, "controlled_image_authorized": args.consent_controlled_screenshot,
              "checks": []}
    output = ROOT / ".artifacts" / "nvidia-diagnosis.json"
    output.parent.mkdir(exist_ok=True)

    def save():
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")

    def check(kind, operation):
        started = time.perf_counter()
        try:
            value = operation()
            report[kind + "_verified"] = True
            report["checks"].append({"phase": kind, "successful": True,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "response_model": provider.last_model, "response_id": provider.last_response_id,
                "request_id": provider.last_request_id, "http_status": provider.last_http_status,
                "validated_type": type(value).__name__})
            print(f"{kind.upper()}: actual NVIDIA response received and validated.", flush=True)
            return True
        except ProviderError as error:
            report["checks"].append({"phase": kind, "successful": False,
                "http_status": error.status_code or provider.last_http_status,
                "request_id": provider.last_request_id, "error_code": error.code,
                "safe_message": str(error),
                "latency_ms": round((time.perf_counter() - started) * 1000, 2)})
            print(f"{kind.upper()}: {error.code}; HTTP {error.status_code or 'unavailable'}. {error}", flush=True)
            if error.status_code in {401, 403}:
                print("Check the current key's Public API Endpoints permission and model access in NVIDIA.", flush=True)
            elif error.status_code == 402:
                print("NVIDIA reported a credits/billing restriction; check the NVIDIA account console.", flush=True)
            elif error.status_code in {502, 503, 504}:
                print("NVIDIA returned a gateway/service error. A Playground reply uses a different session route.", flush=True)
            if provider.last_request_id:
                print("NVIDIA request ID: " + provider.last_request_id, flush=True)
            print("Support details: docs/nvidia-support-request.md. Never include the API key.", flush=True)
            return False
        finally:
            save()

    if not check("text", lambda: provider.complete([{"role": "user", "content": "Reply exactly OK."}])):
        print("No image was sent. Safe diagnostic report: .artifacts/nvidia-diagnosis.json", flush=True)
        return 1
    if args.consent_controlled_screenshot:
        screenshot = ROOT / "demo/evaluation/digital/screenshots/case-correct-market.png"
        if not check("image", lambda: observe_screen(screenshot.read_bytes(), "nvidia",
                     NvidiaScreenProvider(provider), cloud_consent=True)):
            return 1
    else:
        print("Image check skipped. Add --consent-controlled-screenshot to authorize the owned synthetic image.")
    print("Safe diagnostic report: .artifacts/nvidia-diagnosis.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
