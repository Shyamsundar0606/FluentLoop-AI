"""Explicit compact-model download; never imported by app startup."""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    parser.add_argument("--download-compact-models", action="store_true", required=True)
    parser.add_argument("--asr-model", choices=("tiny", "base"), default="tiny")
    args = parser.parse_args()
    root = Path(args.destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import snapshot_download, HfApi

    repo = f"Systran/faster-whisper-{args.asr_model}"
    asr_directory = "asr" if args.asr_model == "tiny" else "asr-base"
    revision = HfApi().model_info(repo).sha
    snapshot_download(
        repo,
        revision=revision,
        local_dir=root / asr_directory,
        allow_patterns=[
            "model.bin",
            "config.json",
            "tokenizer.json",
            "vocabulary.*",
            "preprocessor_config.json",
        ],
    )
    voice_repo = "rhasspy/piper-voices"
    voice_revision = HfApi().model_info(voice_repo).sha
    (root / "tts").mkdir(exist_ok=True)
    for name in [
        "fr_FR-siwis-medium.onnx",
        "fr_FR-siwis-medium.onnx.json",
        "MODEL_CARD",
    ]:
        url = f"https://huggingface.co/{voice_repo}/resolve/{voice_revision}/fr/fr_FR/siwis/medium/{name}"
        target = root / "tts" / name
        with urllib.request.urlopen(url, timeout=60) as response, target.open(
            "wb"
        ) as out:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 80_000_000:
                    raise ValueError("Unexpected model size")
                out.write(chunk)
    manifest = {
        "asr_repository": repo,
        "asr_revision": revision,
        "voice_repository": voice_repo,
        "voice_revision": voice_revision,
        "files": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in (root / asr_directory, root / "tts")
            for p in folder.rglob("*")
            if p.is_file() and ".cache" not in p.parts
        },
    }
    manifest_name = "manifest.json" if args.asr_model == "tiny" else "manifest-base.json"
    (root / manifest_name).write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Provisioned {args.asr_model}; revisions and SHA-256 recorded in {manifest_name}")


if __name__ == "__main__":
    main()
