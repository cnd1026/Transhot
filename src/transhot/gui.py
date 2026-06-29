import os
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from transhot.image_renderer import ImageRenderer
from transhot.ocr import EasyOcrService
from transhot.processing_logger import ProcessingLogger
from transhot.translator import OpenAiTranslator


class Worker(QObject):
    finished = Signal(str)
    failed = Signal(str)
    log_message = Signal(str)

    def __init__(self, image_path: Path, output_dir: Path) -> None:
        super().__init__()
        self._image_path = image_path
        self._output_dir = output_dir

    def run(self) -> None:
        try:
            self.log_message.emit("Image loaded")
            regions = self._extract_regions()
            translated_regions = self._translate_regions(regions)
            output_path = self._render_output(translated_regions)
            self.log_message.emit("Completed")
            self.finished.emit(str(output_path))
        except Exception as exc:
            self.log_message.emit(f"ERROR: {exc}")
            self.failed.emit(str(exc))

    def _extract_regions(self):
        self.log_message.emit("OCR started.")
        regions = EasyOcrService().extract(self._image_path)
        self.log_message.emit("OCR finished")
        self.log_message.emit(f"Detected {len(regions)} text regions")
        if not regions:
            raise RuntimeError("이미지에서 텍스트를 찾지 못했습니다.")
        return regions

    def _translate_regions(self, regions):
        self.log_message.emit("Translation started")
        translator = OpenAiTranslator()
        translated_regions = []
        total_regions = len(regions)
        for index, region in enumerate(regions, start=1):
            self.log_message.emit(f"Translating {index} / {total_regions}")
            translated_regions.extend(translator.translate_regions([region]))
        self.log_message.emit("Translation finished")
        return translated_regions

    def _render_output(self, translated_regions):
        self.log_message.emit("Rendering started")
        self.log_message.emit("Saving output...")
        output_path = ImageRenderer().render(
            self._image_path,
            translated_regions,
            self._output_dir,
        )
        self.log_message.emit("Rendering finished")
        return output_path


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Transhot MVP")
        self.setMinimumSize(640, 520)
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self._last_output_path: Path | None = None
        self._output_dir = Path.cwd() / "output"
        self._logger = ProcessingLogger(Path.cwd() / "logs")

        self._status_label = QLabel("이미지 파일을 선택하세요.")
        self._select_button = QPushButton("이미지 선택 및 번역")
        self._select_button.clicked.connect(self._select_image)

        self._preview_label = QLabel("번역 완료 후 결과 이미지가 여기에 표시됩니다.")
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumSize(560, 360)
        self._preview_label.setStyleSheet("border: 1px solid #cccccc; background: #fafafa;")

        self._open_output_button = QPushButton("결과 폴더 열기")
        self._open_output_button.setEnabled(False)
        self._open_output_button.clicked.connect(self._open_output_folder)

        self._log_label = QLabel("Processing Log")
        self._clear_log_button = QPushButton("Clear Log")
        self._clear_log_button.clicked.connect(self.clear_log)
        log_header_layout = QHBoxLayout()
        log_header_layout.addWidget(self._log_label)
        log_header_layout.addStretch()
        log_header_layout.addWidget(self._clear_log_button)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMinimumHeight(140)

        layout = QVBoxLayout()
        layout.addWidget(self._status_label)
        layout.addWidget(self._preview_label, stretch=1)
        layout.addWidget(self._select_button)
        layout.addWidget(self._open_output_button)
        layout.addLayout(log_header_layout)
        layout.addWidget(self._log_text)

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
        self.clear_log()
        self._logger.start_new_run()
        self._select_button.setEnabled(False)
        self._open_output_button.setEnabled(False)
        self._status_label.setText("OCR 및 번역 처리 중입니다. 첫 실행은 시간이 걸릴 수 있습니다.")

        self._thread = QThread()
        self._worker = Worker(image_path, self._output_dir)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.log_message.connect(self.append_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_finished(self, output_path: str) -> None:
        self._last_output_path = Path(output_path)
        self._select_button.setEnabled(True)
        self._open_output_button.setEnabled(True)
        self._status_label.setText(f"완료: {output_path}")
        self._show_preview(self._last_output_path)
        self.append_log("Processing completed successfully.")
        QMessageBox.information(self, "완료", f"결과 이미지를 저장했습니다.\n{output_path}")
        self._cleanup_worker()

    def _on_failed(self, message: str) -> None:
        self._select_button.setEnabled(True)
        self._status_label.setText("처리 실패")
        QMessageBox.critical(self, "오류", message)
        self._cleanup_worker()

    def append_log(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self._logger.write(line)

        if message.startswith("ERROR:"):
            self._log_text.append(f'<span style="color: #c62828;">{escape(line)}</span>')
        else:
            self._log_text.append(escape(line))

        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self) -> None:
        self._log_text.clear()

    def _show_preview(self, image_path: Path) -> None:
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self._preview_label.setText("결과 이미지를 미리보기로 불러오지 못했습니다.")
            return

        scaled = pixmap.scaled(
            self._preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled)

    def _open_output_folder(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(self._output_dir)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._last_output_path:
            self._show_preview(self._last_output_path)

    def _cleanup_worker(self) -> None:
        self._worker = None
        self._thread = None
