from pathlib import Path
from zipfile import ZipFile


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def extract(zip_path: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_root = destination_dir.resolve()

    with ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target_path = (destination_dir / member.filename).resolve()
            if not target_path.is_relative_to(destination_root):
                continue
            archive.extract(member, destination_dir)


def find_images(input_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def compress(source_dir: Path, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, "w") as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir))

    return zip_path
