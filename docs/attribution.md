# License and attribution

ReplayLab-owned source, planning documents, generated synthetic physical/CodeLab
demo media, and its recorded application demonstration are covered by the
repository [MIT license](../LICENSE). CodeLab is a fictional browser simulation,
not VS Code or a real extension marketplace. The bundled examples use generated
graphics rather than third-party tutorial videos or stock images.

Dependencies and their model artifacts retain their own licenses and notices.
Principal components include React, Vite, Tailwind CSS, React Flow, Lucide,
FastAPI, Pydantic, SQLAlchemy, HTTPX, OpenCV, NumPy, Pillow, pytest, Vitest, nginx,
FFmpeg, RapidOCR, and ONNX Runtime. Installing them does not relicense their
contents under ReplayLab's MIT license.

## Local OCR models

RapidOCR 3.10.0 includes local ONNX model files in its installed wheel. They are
installed dependencies, not ReplayLab-authored weights or tracked demo assets.
The package's `licenses/LICENSE` identifies its source as Apache-2.0;
`licenses/MODEL_LICENSES.md` separately attributes PaddleOCR-derived weights to
Baidu/the applicable PaddleOCR rights holders and records their Apache-2.0 terms,
provenance, hashes, and redistribution notices.

ReplayLab uses `PP-OCRv6_det_small.onnx`, `ch_ppocr_mobile_v2.0_cls_mobile.onnx`, and
`PP-OCRv6_rec_small.onnx` from that installation. Preserve the package's complete
model notice when distributing an environment/container containing these files.
See the [RapidOCR project](https://github.com/RapidAI/RapidOCR) and
[PaddleOCR project](https://github.com/PaddlePaddle/PaddleOCR) for upstream records.

ONNX Runtime 1.31.1 supplies `LICENSE` and `ThirdPartyNotices.txt`; its distribution
identifies the MIT license. Preserve those independent notices as applicable.
Fonts loaded from an operating system or container retain their own licenses.

## Other media and service terms

FFmpeg terms depend on the selected binary and enabled codecs; inspect
`ffmpeg -L` and distributor notices for redistribution. Meta API and SAM parser
terms apply independently of ReplayLab's license. Consult the installed parser
notice and [official Meta documentation](https://dev.meta.ai/docs/quickstart).

User uploads/transcripts remain user-provided content; confirming usage rights
does not assign them ReplayLab's license. YouTube playback uses the original
embedded player and applicable platform terms, without a server-downloaded copy.

The original physical screenshots and recording show actual application behavior
using explicit synthetic fixtures. Digital CodeLab references are generated;
screen OCR reads actual captured pixels. These artifacts are not evidence of live
Meta inference, real software installation, or general model accuracy.
