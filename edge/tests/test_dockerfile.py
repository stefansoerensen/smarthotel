from pathlib import Path

DOCKERFILE = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text()


def test_no_volume_instruction() -> None:
    # Railway refuses images with VOLUME; volumes are attached in the Railway service instead.
    assert not any(line.strip().upper().startswith("VOLUME") for line in DOCKERFILE.splitlines())
