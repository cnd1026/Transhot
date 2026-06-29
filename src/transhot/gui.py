from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from transhot.processor import ImageTranslationProcessor


class Worker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, image_path: Path, output_dir: Path) -> None:
        super().__init__()
        self._image_path = image_path
        self._output_dir = output_dir

    def run(self) -> None:
        try:
            processor = ImageTranslationProcessor()
            output_path = processor.process(self._image_path, self._output_dir)
            self.finished.emit(str(output_path))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Transhot MVP")
        self.setMinimumSize(420, 180)
        self._thread: QThread | None = None
        self._worker: Worker | None = None

        self._status_label = QLabel("이미지 파일을 선택하세요.")
        self._select_button = QPushButton("이미지 선택 및 번역")
        self._select_button.clicked.connect(self._select_image)

        layout = QVBoxLayout()
        layout.addWidget(self._status_label)
        layout.addWidget(self._select_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _select_image(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 선택",
            "",
            "Images (*.jpg *.jpeg *.png *.webp)",
        )
        if not file_name:
            return

        self._start_processing(Path(file_name))

    def _start_processing(self, image_path: Path) -> None:
        self._select_button.setEnabled(False)
        self._status_label.setText("OCR 및 번역 처리 중입니다. 첫 실행은 시간이 걸릴 수 있습니다.")

        output_dir = Path.cwd() / "output"
        self._thread = QThread()
        self._worker = Worker(image_path, output_dir)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_finished(self, output_path: str) -> None:
        self._select_button.setEnabled(True)
        self._status_label.setText(f"완료: {output_path}")
        QMessageBox.information(self, "완료", f"결과 이미지를 저장했습니다.\n{output_path}")
        self._cleanup_worker()

    def _on_failed(self, message: str) -> None:
        self._select_button.setEnabled(True)
        self._status_label.setText("처리 실패")
        QMessageBox.critical(self, "오류", message)
        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        self._worker = None
        self._thread = None
