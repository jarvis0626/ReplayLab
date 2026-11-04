"""Install pinned local Meta Llama CPU/Vulkan artifacts inside this repository."""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / ".artifacts" / "local-meta"
MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
MODEL_FILE = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
MODEL_COMMIT = "5ab33fa94d1d04e903623ae72c95d1696f09f9e8"
MODEL_SIZE = 2019377696
MODEL_SHA256 = "6c1a2b41161032677be168d354123594c0e6e67d2b9227c84f296ad037c728ff"
MODEL_URL = (
    "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/"
    + MODEL_COMMIT + "/" + MODEL_FILE
)
RUNTIME_FILE = "llama-b11960-bin-win-cpu-x64.zip"
RUNTIME_SIZE = 24407745
RUNTIME_SHA256 = "73f962f82850d244db47eaacb9d913637027b82399124324298576d58c5f4287"
RUNTIME_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b11960/" + RUNTIME_FILE
MODELS = {
    "3b": {"id": MODEL_ID, "file": MODEL_FILE, "commit": MODEL_COMMIT,
           "size": MODEL_SIZE, "sha256": MODEL_SHA256},
    "1b": {"id": "meta-llama/Llama-3.2-1B-Instruct", "file": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
           "commit": "067b946cf014b7c697f3654f621d577a3e3afd1c", "size": 807694464,
           "sha256": "6f85a640a97cf2bf5b8e764087b1e83da0fdb51d7c9fab7d0fece9385611df83"},
}
RUNTIMES = {
    "cpu": {"file": RUNTIME_FILE, "size": RUNTIME_SIZE, "sha256": RUNTIME_SHA256, "directory": "runtime"},
    "vulkan": {"file": "llama-b11960-bin-win-vulkan-x64.zip", "size": 37345851,
               "sha256": "bac6914b5e83523eb008c6789eaa12669f93fbc196c3b9e8237b6672323b33e9", "directory": "runtime-vulkan"},
}


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def inside(path: Path) -> Path:
    resolved = path.resolve()
    if not DIRECTORY.resolve().is_relative_to(ROOT.resolve()) or not resolved.is_relative_to(DIRECTORY.resolve()):
        raise ValueError("Local model files must stay inside this repository's artifact directory.")
    return resolved


def verified_download(filename: str, url: str, size: int, expected: str) -> Path:
    target = inside(DIRECTORY / filename)
    if target.exists():
        if target.stat().st_size != size or digest(target) != expected:
            raise ValueError("Existing local artifact failed its integrity check: " + filename)
        print("Verified existing artifact: " + filename, flush=True)
        return target
    # Reuse the already verified prototype archive when present, without a second download.
    cached = next((ROOT / ".artifacts" / name / filename for name in ["local-vision", "local-meta-vulkan"]
                   if (ROOT / ".artifacts" / name / filename).is_file()
                   and (ROOT / ".artifacts" / name / filename).resolve().is_relative_to(ROOT.resolve())
                   and (ROOT / ".artifacts" / name / filename).stat().st_size == size
                   and digest(ROOT / ".artifacts" / name / filename) == expected), None)
    if cached is not None:
        shutil.copyfile(cached, target)
    else:
        partial = inside(target.with_suffix(target.suffix + ".partial"))
        print("Downloading " + filename + " into ignored local artifacts.", flush=True)
        started = last = time.monotonic()
        count = 0
        with urllib.request.urlopen(url, timeout=30) as response, partial.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                count += len(chunk)
                if count > size or time.monotonic() - started > 900:
                    raise ValueError("Local download exceeded its bounded size or duration.")
                output.write(chunk)
                if time.monotonic() - last > 10:
                    print(f"{filename}: {count:,} / {size:,} bytes", flush=True)
                    last = time.monotonic()
        if count != size or digest(partial) != expected:
            raise ValueError("Downloaded artifact failed its pinned integrity check: " + filename)
        partial.replace(target)
    if target.stat().st_size != size or digest(target) != expected:
        raise ValueError("Local artifact failed its pinned integrity check: " + filename)
    return target


def extract_runtime(archive: Path, directory: str = "runtime") -> list[dict]:
    destination = inside(DIRECTORY / directory)
    destination.mkdir(exist_ok=True)
    entries = []
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            normalized = member.filename.replace("\\", "/")
            name = PurePosixPath(normalized)
            if name.is_absolute() or ".." in name.parts or ":" in normalized:
                raise ValueError("Unsafe archive path rejected.")
            if stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError("Archive symbolic links are not accepted.")
            target = inside(destination / normalized)
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Archive path escaped the runtime directory.")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            entries.append({"file": target.relative_to(DIRECTORY).as_posix(), "sha256": digest(target)})
    if not (destination / "llama-server.exe").is_file():
        raise ValueError("Verified archive did not contain the expected server.")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activate", action="store_true", help="Explicitly select local Meta in the ignored API configuration.")
    parser.add_argument("--backend", choices=RUNTIMES, default="cpu")
    parser.add_argument("--model-size", choices=MODELS, default="3b")
    parser.add_argument("--device", default="Vulkan0", help="Explicit Vulkan device from llama-server --list-devices.")
    parser.add_argument("--context-size", type=int, choices=[2048, 4096, 8192], default=None)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This pinned portable setup supports Windows x64 only.")
    if not re.fullmatch(r"Vulkan[0-9]+", args.device):
        parser.error("Choose an explicit Vulkan device such as Vulkan0 or Vulkan1.")
    selected_model, selected_runtime = MODELS[args.model_size], RUNTIMES[args.backend]
    distribution = "bartowski/" + selected_model["id"].split("/", 1)[1] + "-GGUF"
    model_url = "https://huggingface.co/" + distribution + "/resolve/" + selected_model["commit"] + "/" + selected_model["file"]
    runtime_url = "https://github.com/ggml-org/llama.cpp/releases/download/b11960/" + selected_runtime["file"]
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    inside(DIRECTORY)
    model = verified_download(selected_model["file"], model_url, selected_model["size"], selected_model["sha256"])
    archive = verified_download(selected_runtime["file"], runtime_url, selected_runtime["size"], selected_runtime["sha256"])
    files = extract_runtime(archive, selected_runtime["directory"])
    notices = ROOT / "docs" / "third-party" / "llama3.2"
    for filename in ["LICENSE", "USE_POLICY.md", "NOTICE.txt", "LLAMA_CPP_LICENSE"]:
        source = notices / filename
        if not source.is_file():
            raise ValueError("Required third-party notice is missing: " + filename)
        shutil.copyfile(source, inside(DIRECTORY / filename))
    manifest = {
        "schema_version": 1, "model_id": selected_model["id"],
        "model_file": model.relative_to(DIRECTORY).as_posix(), "model_bytes": selected_model["size"],
        "model_sha256": selected_model["sha256"], "model_source": model_url, "model_commit": selected_model["commit"],
        "distribution": distribution, "quantization": "Q4_K_M",
        "modality": "text reasoning over local OCR and supplied transcript; no model vision",
        "runtime_release": "b11960", "runtime_archive_sha256": selected_runtime["sha256"],
        "runtime_executable": selected_runtime["directory"] + "/llama-server.exe", "runtime_files": files,
        "runtime_backend": args.backend, "runtime_device": args.device if args.backend == "vulkan" else None,
        "context_size": args.context_size or (4096 if args.backend == "vulkan" else 8192),
    }
    (DIRECTORY / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if args.activate:
        from dotenv import set_key

        target = ROOT / "apps" / "api" / ".env"
        target.touch(exist_ok=True)
        for name, value in {
            "AI_PROVIDER": "local_meta", "LOCAL_META_BASE_URL": "http://127.0.0.1:8083/v1",
            "LOCAL_META_MODEL": selected_model["id"], "LOCAL_META_TIMEOUT_SECONDS": "120",
        }.items():
            set_key(str(target), name, value)
        print("Local Meta explicitly selected in ignored apps/api/.env. Existing provider credentials were preserved.")
    print("Verified " + selected_model["id"] + " and " + args.backend + " runtime are ready. Built with Llama.")
    print("Start with: .venv\\Scripts\\python.exe scripts/run-local-meta.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print("Local Meta setup failed: " + str(error), file=sys.stderr)
        raise SystemExit(1) from None
