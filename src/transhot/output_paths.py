from pathlib import Path


def make_unique_output_path(source_path: Path, prefix: str = "re_") -> Path:
    base_path = source_path.with_name(f"{prefix}{source_path.stem}{source_path.suffix}")
    if not base_path.exists():
        return base_path

    index = 1
    while True:
        candidate = source_path.with_name(f"{prefix}{source_path.stem}_{index}{source_path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
