# Local Meta model notices

ReplayLab's optional local provider uses **Meta Llama 3.2 3B Instruct**, with a
community Q4_K_M GGUF conversion from bartowski. The model processes text from
local OCR and supplied tutorial transcripts. It does not perform model vision,
SAM segmentation, or Muse Glimmer inference.

- [Original Meta model](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct)
- [Pinned community distribution](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/tree/5ab33fa94d1d04e903623ae72c95d1696f09f9e8)
- [Official model license](LICENSE), [acceptable use policy](USE_POLICY.md), and
  [attribution notice](NOTICE.txt)
- [llama.cpp runtime license](LLAMA_CPP_LICENSE)

The setup script verifies pinned SHA256 hashes and stores the model, portable
Windows CPU runtime, and copies of these notices under ignored
`.artifacts/local-meta/`. Model weights and executable files are not committed.

```powershell
.venv\Scripts\python.exe scripts/setup-local-meta.py
.venv\Scripts\python.exe scripts/run-local-meta.py
```

Adding `--activate` to setup explicitly selects the local provider in ignored
`apps/api/.env`, while preserving existing cloud credentials. Restart ReplayLab
after changing its provider configuration. The runner binds only to
`127.0.0.1:8083`, disables its Web UI, uses CPU inference, and strips cloud API
credentials from its child process environment. `run-local-meta.py --check-ready`
returns success only when the expected model is healthy at that local endpoint.

Built with Llama.
