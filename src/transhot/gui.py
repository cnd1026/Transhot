import os
from datetime import datetime
from html import escape
from pathlib import Path
from zipfile import BadZipFile

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from transhot.image_renderer import ImageRenderer
from transhot.ocr import EasyOcrService
from transhot.output_paths import make_unique_output_path
from transhot.processing_logger import ProcessingLogger
from transhot.settings import AppSettings, SettingsStore
from transhot.translator import OpenAiTranslator
from transhot.zip_processor import compress, extract, find_images


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | {".zip"}
DEFAULT_PREVIEW_TEXT = "Select or drag an image/ZIP file to start."
DROP_PREVIEW_TEXT = "Drop image or ZIP file here"


class SettingsDialog(QDialog):
    def __init__(self, settings_store: SettingsStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._settings_store = settings_store

        settings = self._settings_store.load()
        self._api_key_input = QLineEdit(settings.openai_api_key)
        self._api_key_input.setEchoMode(QLineEdit.Password)
        self._api_key_input.setMinimumWidth(360)

        form_layout = QFormLayout()
        form_layout.addRow("OpenAI API Key", self._api_key_input)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self._save)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    def _save(self) -> None:
        self._settings_store.save(AppSettings(openai_api_key=self._api_key_input.text().strip()))
        self.accept()


class Worker(QObject):
    finished = Signal(str)
    failed = Signal(str)
    log_message = Signal(str)

    def __init__(self, input_path: Path, output_dir: Path, temp_dir: Path) -> None:
        super().__init__()
        self._input_path = input_path
        self._output_dir = output_dir
        self._temp_dir = temp_dir
        self._ocr_service = EasyOcrService()
        self._renderer = ImageRenderer()
        self._translator: OpenAiTranslator | None = None

    def run(self) -> None:
        try:
            if self._input_path.suffix.lower() == ".zip":
                output_path = self._process_zip()
            else:
                output_path = self._process_image(
                    self._input_path,
                    self._input_path.parent,
                    make_unique_output_path(self._input_path),
                )
            self.log_message.emit("Completed")
            self.finished.emit(str(output_path))
        except BadZipFile:
            self.log_message.emit("ERROR: ZIP 파일이 손상되었거나 읽을 수 없습니다.")
            self.failed.emit("ZIP 파일이 손상되었거나 읽을 수 없습니다.")
        except Exception as exc:
            self.log_message.emit(f"ERROR: {exc}")
            self.failed.emit(str(exc))

    def _process_image(
        self,
        image_path: Path,
        output_dir: Path,
        output_path: Path | None = None,
        log_output_path: bool = True,
    ) -> Path:
        self.log_message.emit("Image loaded")
        regions = self._extract_regions(image_path)
        translated_regions = self._translate_regions(regions)
        return self._render_output(
            image_path,
            translated_regions,
            output_dir,
            output_path,
            log_output_path,
        )

    def _process_zip(self) -> Path:
        self.log_message.emit("ZIP detected.")
        input_dir = self._temp_dir / "input"
        temp_output_dir = self._temp_dir / "output"
        temp_output_dir.mkdir(parents=True, exist_ok=True)

        self.log_message.emit("Extracting...")
        extract(self._input_path, input_dir)

        image_paths = find_images(input_dir)
        total_images = len(image_paths)
        if total_images == 0:
            raise RuntimeError("ZIP 파일 안에서 지원하는 이미지 파일을 찾지 못했습니다.")

        for index, image_path in enumerate(image_paths, start=1):
            self.log_message.emit(f"Image {index} / {total_images}")
            relative_parent = image_path.relative_to(input_dir).parent
            image_output_dir = temp_output_dir / relative_parent
            try:
                self._process_image(image_path, image_output_dir, log_output_path=False)
            except Exception as exc:
                self.log_message.emit(f"ERROR: Skipping {image_path.relative_to(input_dir)} - {exc}")

        self.log_message.emit("Compressing...")
        zip_output_path = make_unique_output_path(self._input_path)
        compress(temp_output_dir, zip_output_path)
        self.log_message.emit(f"Output saved: {zip_output_path}")
        self.log_message.emit("ZIP completed.")
        return zip_output_path

    def _extract_regions(self, image_path: Path):
        self.log_message.emit("OCR started.")
        regions = self._ocr_service.extract(image_path)
        self.log_message.emit("OCR finished")
        self.log_message.emit(f"Detected {len(regions)} text regions")
        if not regions:
            raise RuntimeError("이미지에서 텍스트를 찾지 못했습니다.")
        return regions

    def _translate_regions(self, regions):
        self.log_message.emit("Translation started")
        translator = self._get_translator()
        translated_regions = []
        total_regions = len(regions)
        for index, region in enumerate(regions, start=1):
            self.log_message.emit(f"Translating {index} / {total_regions}")
            translated_regions.extend(translator.translate_regions([region]))
        self.log_message.emit("Translation finished")
        return translated_regions

    def _render_output(
        self,
        image_path: Path,
        translated_regions,
        output_dir: Path,
        output_path: Path | None = None,
        log_output_path: bool = True,
    ):
        self.log_message.emit("Rendering started")
        self.log_message.emit("Saving output...")
        output_path = self._renderer.render(
            image_path,
            translated_regions,
            output_dir,
            output_path,
        )
        if log_output_path:
            self.log_message.emit(f"Output saved: {output_path}")
        self.log_message.emit("Rendering finished")
        return output_path

    def _get_translator(self) -> OpenAiTranslator:
        if self._translator is None:
            self._translator = OpenAiTranslator()
        return self._translator


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Transhot MVP")
        self.setMinimumSize(640, 520)
        self.setAcceptDrops(True)
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self._last_output_path: Path | None = None
        self._output_dir = Path.cwd() / "output"
        self._temp_root = Path.cwd() / "temp"
        self._logger = ProcessingLogger(Path.cwd() / "logs")
        self._settings_store = SettingsStore()
        self._settings_store.ensure_exists()

        self._status_label = QLabel("이미지 파일을 선택하세요.")
        self._select_button = QPushButton("이미지 선택 및 번역")
        self._select_button.clicked.connect(self._select_image)
        self._settings_button = QPushButton("API Key")
        self._settings_button.clicked.connect(self._open_settings)

        self._preview_label = QLabel(DEFAULT_PREVIEW_TEXT)
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

        action_layout = QHBoxLayout()
        action_layout.addWidget(self._select_button)
        action_layout.addWidget(self._settings_button)
        action_layout.addWidget(self._open_output_button)

        layout = QVBoxLayout()
        layout.addWidget(self._status_label)
        layout.addWidget(self._preview_label, stretch=1)
        layout.addLayout(action_layout)
        layout.addLayout(log_header_layout)
        layout.addWidget(self._log_text)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _select_image(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 또는 ZIP 선택",
            "",
            "Supported Files (*.jpg *.jpeg *.png *.webp *.zip)",
        )
        if not file_name:
            return

        self._handle_input_path(Path(file_name))

    def _handle_input_path(self, input_path: Path) -> None:
        if self._worker is not None:
            self.append_log("ERROR: Processing is already running.")
            return

        if not self._is_supported_file(input_path):
            self.append_log(f"ERROR: Unsupported file type: {input_path.name}")
            return

        if not self._has_api_key():
            QMessageBox.warning(
                self,
                "API Key 필요",
                "OpenAI API Key가 설정되어 있지 않습니다.\nAPI Key 버튼을 눌러 먼저 저장해주세요.",
            )
            self._open_settings()
            return

        self._start_processing(input_path)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._settings_store, self)
        if dialog.exec() == QDialog.Accepted:
            QMessageBox.information(self, "저장 완료", "OpenAI API Key를 저장했습니다.")

    def _has_api_key(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY") or self._settings_store.load().openai_api_key.strip())

    def _is_supported_file(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS

    def _start_processing(self, image_path: Path) -> None:
        self.clear_log()
        self._logger.start_new_run()
        self._select_button.setEnabled(False)
        self._open_output_button.setEnabled(False)
        self._status_label.setText("OCR 및 번역 처리 중입니다. 첫 실행은 시간이 걸릴 수 있습니다.")
        self._preview_label.setText("Processing...")

        self._thread = QThread()
        temp_dir = self._temp_root / datetime.now().strftime("%Y%m%d_%H%M%S")
        self._worker = Worker(image_path, self._output_dir, temp_dir)
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
        if self._last_output_path.suffix.lower() in IMAGE_EXTENSIONS:
            self._show_preview(self._last_output_path)
        else:
            self._preview_label.setText(f"ZIP 결과 저장 완료:\n{output_path}")
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
        output_folder = self._last_output_path.parent if self._last_output_path else self._output_dir
        output_folder.mkdir(parents=True, exist_ok=True)
        os.startfile(output_folder)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._last_output_path and self._last_output_path.suffix.lower() in IMAGE_EXTENSIONS:
            self._show_preview(self._last_output_path)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._preview_label.setText(DROP_PREVIEW_TEXT)
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._restore_preview_after_drop()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        supported_paths = [path for path in paths if self._is_supported_file(path)]

        if not supported_paths:
            for path in paths:
                self.append_log(f"ERROR: Unsupported file type: {path.name}")
            if not paths:
                self.append_log("ERROR: Unsupported file type: dropped item")
            self._restore_preview_after_drop()
            event.acceptProposedAction()
            return

        if len(paths) > 1:
            self.append_log("Multiple files dropped. Processing first supported file only.")

        self._handle_input_path(supported_paths[0])
        if self._worker is None:
            self._restore_preview_after_drop()
        event.acceptProposedAction()

    def _restore_preview_after_drop(self) -> None:
        if self._last_output_path is None:
            self._preview_label.setText(DEFAULT_PREVIEW_TEXT)
        elif self._last_output_path.suffix.lower() in IMAGE_EXTENSIONS:
            self._show_preview(self._last_output_path)
        else:
            self._preview_label.setText(f"ZIP 결과 저장 완료:\n{self._last_output_path}")

    def _cleanup_worker(self) -> None:
        self._worker = None
        self._thread = None
