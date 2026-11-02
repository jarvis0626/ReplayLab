"""Real text/image probes on repository-owned content; credentials stay local."""

import base64
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))


def main():
    import httpx
    from dotenv import dotenv_values
    from pydantic import BaseModel, ConfigDict

    config = dotenv_values(ROOT / "apps" / "api" / ".env")
    key = os.environ.get("NVIDIA_API_KEY") or config.get("NVIDIA_API_KEY")
    if not key:
        raise SystemExit("NVIDIA_API_KEY is not configured; no requests sent.")
    model = config.get("NVIDIA_MODEL") or "meta/muse-glimmer-30b"
    output = ROOT / ".artifacts" / "nvidia-probes.json"
    output.parent.mkdir(exist_ok=True)

    class VisionProbe(BaseModel):
        model_config = ConfigDict(extra="forbid")
        application: str
        panel: str
        visible_labels: list[str]

    content = base64.b64encode((ROOT / "demo/evaluation/digital/screenshots/case-correct-market.png").read_bytes()).decode()
    probes = [
        ("text", [{"type": "text", "text": 'Return JSON only: {"ok":true}.'}]),
        ("image", [
            {"type": "text", "text": 'Read this synthetic application screenshot. Return only a JSON object with application (string), panel (string), visible_labels (list of exact visible strings). Never infer hidden state.'},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + content}},
        ]),
    ]
    report = []
    with httpx.Client(timeout=httpx.Timeout(90, connect=15)) as client:
        for kind, message in probes:
            started = time.perf_counter()
            try:
                response = client.post("https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={"Authorization": "Bearer " + key}, json={
                        "model": model, "messages": [{"role": "user", "content": message}],
                        "temperature": .95, "top_p": 1, "max_tokens": 1024,
                        "reasoning_effort": "minimal", "stream": False,
                    })
                item = {"probe": kind, "http_status": response.status_code,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "configured_model": model, "ok": False}
                if response.is_success:
                    body = response.json()
                    text = body["choices"][0]["message"]["content"].strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    value = json.loads(text)
                    if kind == "text":
                        item["ok"] = value == {"ok": True}
                    else:
                        observed = VisionProbe.model_validate(value)
                        item["observations"] = observed.model_dump()
                        item["ok"] = "extensions" in (observed.panel + " ".join(observed.visible_labels)).casefold()
                    item["returned_model"] = body.get("model")
                    item["response_id"] = body.get("id")
                    item["usage"] = {k: v for k, v in body.get("usage", {}).items() if k in {"prompt_tokens", "completion_tokens", "total_tokens"}}
            except (httpx.RequestError, ValueError, KeyError, TypeError, AttributeError) as error:
                item = {"probe": kind, "ok": False, "error_type": type(error).__name__,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
            report.append(item)
            print(json.dumps(item), flush=True)
            output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if all(item["ok"] for item in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
