"""Export the current API schema without initializing the user's runtime store."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))


def main():
    # main.py exposes its development app at import time. Redirect that temporary
    # store before import, then export a separately configured application.
    import os

    previous = os.environ.get("DATA_DIR")
    with tempfile.TemporaryDirectory(prefix="replaylab-contracts-") as directory:
        os.environ["DATA_DIR"] = directory
        try:
            from app.core.config import Settings
            from app.main import app, create_app

            application = create_app(
                Settings(data_dir=Path(directory), ai_provider="mock")
            )
            target = ROOT / "packages" / "contracts" / "openapi.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(application.openapi(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            application.state.store.engine.dispose()
            app.state.store.engine.dispose()
            print(f"Exported {target.relative_to(ROOT)}")
        finally:
            if previous is None:
                os.environ.pop("DATA_DIR", None)
            else:
                os.environ["DATA_DIR"] = previous


if __name__ == "__main__":
    main()
