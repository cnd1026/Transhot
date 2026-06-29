from datetime import datetime
from pathlib import Path


class ProcessingLogger:
    def __init__(self, log_dir: Path) -> None:
        self._log_dir = log_dir
        self._log_path: Path | None = None

    @property
    def log_path(self) -> Path | None:
        return self._log_path

    def start_new_run(self) -> Path:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self._log_path = self._log_dir / filename
        self._log_path.touch()
        return self._log_path

    def write(self, line: str) -> None:
        if self._log_path is None:
            self.start_new_run()

        assert self._log_path is not None
        with self._log_path.open("a", encoding="utf-8") as file:
            file.write(f"{line}\n")
