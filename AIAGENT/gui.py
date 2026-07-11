import sys
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QTabWidget, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QSplitter, QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from .code_agent import CodeAgent
from .file_handler import extract_text_from_file, validate_file, merge_texts

import traceback


def get_log_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


def log_to_file(msg):
    log_file = get_log_dir() / "app.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


class Worker(QThread):
    finished = pyqtSignal(dict, str)
    progress_update = pyqtSignal(str)

    def __init__(self, tech_task):
        super().__init__()
        self.tech_task = tech_task

    def run(self):
        try:
            agent = CodeAgent()

            def callback(msg: str):
                self.progress_update.emit(msg)

            result = agent.run(self.tech_task, callback)
            self.finished.emit(result, result["log"])
        except Exception:
            error_msg = traceback.format_exc()
            self.finished.emit({"success": False}, f"Ошибка:\n{error_msg}")


class MainWindow(QMainWindow):
    MAX_FILES = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ИИ‑агент: Генерация кода по ТЗ")
        self.setMinimumSize(1400, 900)

        self.attached_files = []
        self.setAcceptDrops(True)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
 
        title = QLabel("Генерация кода по ТЗ")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        main_layout.addWidget(title)
 
        files_panel_layout = QHBoxLayout()
        attach_btn = QPushButton("Прикрепить файл (PDF/DOCX/TXT)")
        attach_btn.setFont(QFont("Arial", 11, QFont.Bold))
        attach_btn.clicked.connect(self.on_attach_file)
        files_panel_layout.addWidget(attach_btn)

        self.files_label = QLabel(f"Файлов: 0/{self.MAX_FILES}")
        self.files_label.setFont(QFont("Arial", 10))
        files_panel_layout.addWidget(self.files_label)
        files_panel_layout.addStretch()
        main_layout.addLayout(files_panel_layout)
 
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(90)
        self.files_list.setFont(QFont("Courier New", 11))
        self.files_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.files_list.customContextMenuRequested.connect(self._show_file_context_menu)
        main_layout.addWidget(self.files_list)
 
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setHandleWidth(8)
        main_layout.addWidget(main_splitter)
 
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setHandleWidth(8)
        main_splitter.addWidget(top_splitter)
 
        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setHandleWidth(8)

        input_label = QLabel("Техническое задание:")
        input_label.setFont(QFont("Arial", 13, QFont.Bold))

        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Courier New", 12))

        left_splitter.addWidget(input_label)
        left_splitter.addWidget(self.input_text)
        top_splitter.addWidget(left_splitter)
 
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setHandleWidth(8)

        log_label = QLabel("Логи:")
        log_label.setFont(QFont("Arial", 13, QFont.Bold))

        self.live_log = QTextEdit()
        self.live_log.setReadOnly(True)
        self.live_log.setFont(QFont("Courier New", 11))

        right_splitter.addWidget(log_label)
        right_splitter.addWidget(self.live_log)
        top_splitter.addWidget(right_splitter)
 
        bottom_block = QWidget()
        bottom_layout = QVBoxLayout(bottom_block)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
 
        buttons_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Сгенерировать проект")
        self.generate_btn.setFont(QFont("Arial", 11, QFont.Bold))
        buttons_layout.addWidget(self.generate_btn)

        self.download_btn = QPushButton("Скачать проект")
        self.download_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.download_btn.setEnabled(False)
        buttons_layout.addWidget(self.download_btn)

        self.status_label = QLabel("Готов")
        self.status_label.setFont(QFont("Arial", 11))
        buttons_layout.addWidget(self.status_label)
        buttons_layout.addStretch()

        bottom_layout.addLayout(buttons_layout)
 
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Courier New", 11))
        bottom_layout.addWidget(self.tabs)
 
        main_splitter.addWidget(bottom_block)
 
        main_splitter.setSizes([600, 400])
        top_splitter.setSizes([700, 700])
        left_splitter.setSizes([50, 500])
        right_splitter.setSizes([50, 500])
 
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(8)
        main_layout.addWidget(self.progress)

        self.apply_styles()

        self.generate_btn.clicked.connect(self.on_generate)
        self.download_btn.clicked.connect(self.on_download)
 
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return

        for url in urls:
            file_path = url.toLocalFile()
            if not file_path:
                continue
            if self._add_file(file_path):
                event.acceptProposedAction()
            else:
                self.status_label.setText(f"Ошибка: {Path(file_path).name} не добавлен")
                event.ignore()

    def _add_file(self, file_path: str) -> bool:
        if len(self.attached_files) >= self.MAX_FILES:
            self.status_label.setText(f"Максимум {self.MAX_FILES} файлов!")
            return False

        valid, error_msg = validate_file(file_path)
        if not valid:
            self.status_label.setText(f"Ошибка: {error_msg}")
            return False

        file_name = Path(file_path).name
        if any(Path(f).name == file_name for f in self.attached_files):
            self.status_label.setText(f"Файл {file_name} уже прикреплён!")
            return False

        self.attached_files.append(file_path)
        self._update_files_list()
        self.status_label.setText(f"Файл {file_name} прикреплён")
        return True

    def _update_files_list(self):
        self.files_list.clear()
        for i, file_path in enumerate(self.attached_files, 1):
            file_name = Path(file_path).name
            item = QListWidgetItem(f"{i}. {file_name}")
            self.files_list.addItem(item)
        self.files_label.setText(f"Файлов: {len(self.attached_files)}/{self.MAX_FILES}")

    def _clear_attached_files(self):
        self.attached_files.clear()
        self._update_files_list()

    def _show_file_context_menu(self, pos):
        if not self.attached_files:
            return
        menu = QMenu()
        remove_action = QAction("Удалить файл", self)
        remove_action.triggered.connect(self._remove_selected_file)
        menu.addAction(remove_action)
        menu.exec_(self.files_list.mapToGlobal(pos))

    def _remove_selected_file(self):
        current_row = self.files_list.currentRow()
        if 0 <= current_row < len(self.attached_files):
            del self.attached_files[current_row]
            self._update_files_list()
            self.status_label.setText("Файл удалён")

    def on_attach_file(self):
        if len(self.attached_files) >= self.MAX_FILES:
            self.status_label.setText(f"Максимум {self.MAX_FILES} файлов!")
            return

        dialog = QFileDialog(self)
        dialog.setWindowTitle("Выберите файлы")
        dialog.setDirectory(str(Path.home() / "Desktop"))
        dialog.setNameFilter("Поддерживаемые файлы (*.txt *.pdf *.docx)")
        dialog.setFileMode(QFileDialog.ExistingFiles)

        if dialog.exec_() == QFileDialog.Accepted:
            for file_path in dialog.selectedFiles():
                self._add_file(file_path)

    def apply_styles(self):
        style = """
            QMainWindow { background: #0f0f23; }
            QLabel { color: #e0e6ff; }
            QTextEdit {
                background-color: #16172e;
                color: #b8c5ff;
                border: 1px solid #2d2f5e;
                border-radius: 8px;
                padding: 10px;
            }
            QListWidget {
                background-color: #16172e;
                color: #b8c5ff;
                border: 1px solid #2d2f5e;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #6b9eff;
                color: #0a0a14;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
            }
            QSplitter::handle {
                background-color: #2d2f5e;
            }
            QTabWidget::pane {
                border: 1px solid #2d2f5e;
                border-radius: 6px;
            }
        """
        self.setStyleSheet(style)

    def on_generate(self):
        manual_text = self.input_text.toPlainText().strip()

        file_texts = []
        for file_path in self.attached_files:
            text = extract_text_from_file(file_path)
            if text and not text.startswith("Ошибка"):
                file_texts.append(text)
            elif text.startswith("Ошибка"):
                self.status_label.setText(text)
                return

        tech_task = merge_texts(manual_text, *file_texts)

        if not tech_task:
            self.status_label.setText("Введите ТЗ или прикрепите файлы!")
            return

        self.generate_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.status_label.setText("Генерация...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.tabs.clear()
        self.live_log.clear()

        self.worker = Worker(tech_task)
        self.worker.finished.connect(self.on_finished)
        self.worker.progress_update.connect(self.on_progress_update)
        self.worker.start()

    def on_progress_update(self, msg: str):
        self.live_log.append(msg)

    def on_finished(self, result, log):
        self.progress.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.status_label.setText("Готово")
        self.download_btn.setEnabled(True)

        base_dir = get_base_dir()
        modules_dir = base_dir / "modules"

        for module_file in sorted(modules_dir.glob("*.py")):
            editor = QTextEdit()
            editor.setReadOnly(True)
            editor.setFont(QFont("Courier New", 12))
            editor.setText(module_file.read_text(encoding="utf-8"))
            self.tabs.addTab(editor, module_file.name)

        self._clear_attached_files()

    def on_download(self):
        target_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения проекта")
        if not target_dir:
            return

        base_dir = get_base_dir()
        modules_dir = base_dir / "modules"
        manifest_file = base_dir / "manifest.json"

        dst = Path(target_dir) / "generated_project"
        dst.mkdir(exist_ok=True)

        shutil.copytree(modules_dir, dst / "modules", dirs_exist_ok=True)
        shutil.copy(manifest_file, dst / "manifest.json")

        self.status_label.setText("Скачано!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 12))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
