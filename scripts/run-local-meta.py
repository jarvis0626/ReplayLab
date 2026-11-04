"""Run the manifest-selected pinned Meta CPU/Vulkan model on loopback."""

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / ".artifacts" / "local-meta"
MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
MODEL_SHA256 = "6c1a2b41161032677be168d354123594c0e6e67d2b9227c84f296ad037c728ff"
RUNTIME_SHA256 = "73f962f82850d244db47eaacb9d913637027b82399124324298576d58c5f4287"
BASE_URL = "http://127.0.0.1:8083"
MODELS = {
    MODEL_ID: {"file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf", "sha256": MODEL_SHA256},
    "meta-llama/Llama-3.2-1B-Instruct": {"file": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "sha256": "6f85a640a97cf2bf5b8e764087b1e83da0fdb51d7c9fab7d0fece9385611df83"},
}
RUNTIMES = {
    "cpu": {"sha256": RUNTIME_SHA256, "executable": "runtime/llama-server.exe"},
    "vulkan": {"sha256": "bac6914b5e83523eb008c6789eaa12669f93fbc196c3b9e8237b6672323b33e9",
               "executable": "runtime-vulkan/llama-server.exe"},
}


def artifact(name: str) -> Path:
    path = (DIRECTORY / name).resolve()
    if not DIRECTORY.resolve().is_relative_to(ROOT.resolve()) or not path.is_relative_to(DIRECTORY.resolve()):
        raise ValueError("Local runtime paths must remain inside this repository's artifact directory.")
    if not path.is_file():
        raise ValueError("Local model setup is incomplete. Run scripts/setup-local-meta.py first.")
    return path


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def healthy() -> bool:
    try:
        expected_model = configuration()["model_id"]
        with httpx.Client(base_url=BASE_URL, timeout=2, trust_env=False, follow_redirects=False) as client:
            if client.get("/health").status_code != 200:
                return False
            response = client.get("/v1/models")
            return response.status_code == 200 and any(
                entry.get("id") == expected_model for entry in response.json().get("data", [])
            )
    except (httpx.RequestError, ValueError, AttributeError, TypeError):
        return False


def configuration() -> dict:
    manifest = json.loads(artifact("manifest.json").read_text(encoding="utf-8"))
    model = MODELS.get(manifest.get("model_id"))
    backend = manifest.get("runtime_backend", "cpu")
    runtime = RUNTIMES.get(backend)
    if (manifest.get("schema_version") != 1 or not model or not runtime
            or manifest.get("model_sha256") != model["sha256"]
            or manifest.get("model_file") != model["file"]
            or manifest.get("runtime_archive_sha256") != runtime["sha256"]
            or manifest.get("runtime_executable") != runtime["executable"]):
        raise ValueError("Local model manifest differs from the pinned setup.")
    if backend == "vulkan" and not re.fullmatch(r"Vulkan[0-9]+", manifest.get("runtime_device", "")):
        raise ValueError("The Vulkan manifest needs an explicit device.")
    if manifest.get("context_size", 8192) not in {2048, 4096, 8192}:
        raise ValueError("Unsupported local model context size.")
    return manifest


def validate_files() -> tuple[Path, Path]:
    manifest = configuration()
    model = artifact(manifest["model_file"])
    executable = artifact(manifest["runtime_executable"])
    if model.name != MODELS[manifest["model_id"]]["file"] or executable.name != "llama-server.exe":
        raise ValueError("Unexpected local model or runtime filename.")
    if digest(model) != manifest["model_sha256"]:
        raise ValueError("Local model failed its pinned SHA256 check.")
    records = manifest.get("runtime_files", [])
    executable_listed = False
    for record in records:
        path = artifact(record["file"])
        if digest(path) != record["sha256"]:
            raise ValueError("Local runtime failed an integrity check.")
        executable_listed |= path == executable
    if not executable_listed:
        raise ValueError("Local runtime executable is absent from the verified manifest.")
    return model, executable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-ready", action="store_true", help="Exit0 only when a healthy local server serves the expected model.")
    args = parser.parse_args()
    if args.check_ready:
        return 0 if healthy() else 1
    if os.name != "nt":
        parser.error("This pinned portable runtime supports Windows x64 only.")
    with socket.socket() as check:
        try:
            check.bind(("127.0.0.1", 8083))
        except OSError:
            raise ValueError("Port8083 is occupied. No existing process was stopped; use --check-ready to inspect the model.") from None
    model, executable = validate_files()
    manifest = configuration()
    backend = manifest.get("runtime_backend", "cpu")
    command = [str(executable), "-m", str(model), "--host", "127.0.0.1", "--port", "8083",
               "--alias", manifest["model_id"], "-ngl", "99" if backend == "vulkan" else "0",
               "--threads", "4" if backend == "vulkan" else "8", "-c", str(manifest.get("context_size", 8192)),
               "--parallel", "1", "--no-webui"]
    if backend == "vulkan":
        command.extend(["--device", manifest["runtime_device"], "--fit", "off"])
    # No API credential is needed or forwarded. This is a foreground child;
    # the caller can stop its process tree with the normal development runner.
    environment = {
        name: value for name, value in os.environ.items()
        if name.upper() not in {
            "NVIDIA_API_KEY", "MODEL_API_KEY", "OPENAI_API_KEY", "HF_TOKEN",
            "HUGGING_FACE_HUB_TOKEN", "LLAMA_API_KEY", "LLAMA_ARG_API_KEY",
        }
    }
    process = subprocess.Popen(command, cwd=DIRECTORY, env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
    record = {"pid": process.pid, "started_at": datetime.now(UTC).isoformat(), "command": command,
              "bind": "127.0.0.1:8083", "credentials_used": False, "state": "running"}
    ownership = DIRECTORY / "server-ownership.json"
    ownership.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    try:
        return process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        return 130
    finally:
        if process.poll() is not None:
            record.update(state="stopped", exit_code=process.returncode, stopped_at=datetime.now(UTC).isoformat())
            ownership.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Local Meta start failed: " + str(error), file=sys.stderr)
        raise SystemExit(1) from None
