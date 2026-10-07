import hashlib
import json
import urllib.request
from pathlib import Path

SAMPLES_DIRECTORY = Path(__file__).resolve().parent
SOURCE_FILE = SAMPLES_DIRECTORY / "official_sources.json"
OUTPUT_DIRECTORY = SAMPLES_DIRECTORY / "official"


def main() -> None:
    sources = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    for source in sources:
        request = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "ocr-exiros-firmas-poc/1.0"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()

        if not content.startswith(b"%PDF"):
            raise RuntimeError(f"{source['filename']} did not return a PDF.")

        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != source["sha256"]:
            raise RuntimeError(
                f"{source['filename']} changed since it was reviewed. "
                f"Expected {source['sha256']}, received {actual_hash}."
            )

        destination = OUTPUT_DIRECTORY / source["filename"]
        destination.write_bytes(content)
        print(f"Downloaded {destination} ({len(content)} bytes)")


if __name__ == "__main__":
    main()
