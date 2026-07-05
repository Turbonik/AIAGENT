import sys
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QTabWidget, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QFont, QPalette, QColor, QDragEnterEvent, QDropEvent, QIcon

from .code_agent import CodeAgent
from .file_handler import extract_text_from_file, validate_file, merge_texts


class Worker(QThread):
    finished = pyqtSignal(dict, str)
    progress_update = pyqtSignal(str)

    def __init__(self, tech_task):
        super().__init__()
        self.tech_task = tech_task

    def run(self):
        agent = CodeAgent()

        def callback(msg: str):
            self.progress_update.emit(msg)

        result = agent.run(self.tech_task, callback)
        self.finished.emit(result, result["log"])


class MainWindow(QMainWindow):
    MAX_FILES = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ИИ‑агент: Генерация кода по ТЗ")
        self.setMinimumSize(1400, 900)

        self.attached_files = []  # Список путей к загруженным файлам

        # Разрешаем drag-drop на главном окне
        self.setAcceptDrops(True)

        central = QWidget()
        central.setAcceptDrops(True)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Генерация кода по ТЗ")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        main_layout.addWidget(title)

        # Панель загрузки файлов
        files_panel_layout = QHBoxLayout()

        attach_btn = QPushButton("📎 Прикрепить файл (PDF/DOCX/TXT)")
        attach_btn.setFont(QFont("Arial", 11, QFont.Bold))
        attach_btn.clicked.connect(self.on_attach_file)
        files_panel_layout.addWidget(attach_btn)

        self.files_label = QLabel(f"Файлов: 0/{self.MAX_FILES}")
        self.files_label.setFont(QFont("Arial", 10))
        files_panel_layout.addWidget(self.files_label)
        files_panel_layout.addStretch()

        main_layout.addLayout(files_panel_layout)

        # Список загруженных файлов (с возможностью удаления)
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(90)
        self.files_list.setFont(QFont("Courier New", 11))
        self.files_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.files_list.customContextMenuRequested.connect(self._show_file_context_menu)
        main_layout.addWidget(self.files_list)

        # Основной разделитель: ТЗ (слева) и Логи (справа)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Левая часть: ТЗ (с drag-drop)
        self.left_container = QWidget()
        self.left_container.setAcceptDrops(True)  # Принимаем сброс файлов
        left = QVBoxLayout(self.left_container)
        left.setContentsMargins(12, 12, 12, 12)

        input_label = QLabel("Техническое задание:")
        input_label.setFont(QFont("Arial", 13, QFont.Bold))
        left.addWidget(input_label)

        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Courier New", 12))
        self.input_text.setMinimumHeight(250)
        self.input_text.setAcceptDrops(True)  # Можно кидать файлы прямо в поле ввода
        left.addWidget(self.input_text)

        splitter.addWidget(self.left_container)
        splitter.setSizes([2, 1])  # Соотношение левой и правой части (2:1)

        # Правая часть: логи
        right_container = QWidget()
        right = QVBoxLayout(right_container)

        log_label = QLabel("Логи :")
        log_label.setFont(QFont("Arial", 13, QFont.Bold))
        right.addWidget(log_label)

        self.live_log = QTextEdit()
        self.live_log.setReadOnly(True)
        self.live_log.setFont(QFont("Courier New", 11))
        right.addWidget(self.live_log)

        splitter.addWidget(right_container)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Сгенерировать проект")
        self.generate_btn.setFont(QFont("Arial", 11, QFont.Bold))
        btn_layout.addWidget(self.generate_btn)

        self.download_btn = QPushButton("Скачать проект")
        self.download_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.download_btn.setEnabled(False)
        btn_layout.addWidget(self.download_btn)

        self.status_label = QLabel("Готов")
        self.status_label.setFont(QFont("Arial", 11))
        btn_layout.addWidget(self.status_label)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # Вкладки с кодом
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Courier New", 11))
        main_layout.addWidget(self.tabs)

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(8)
        main_layout.addWidget(self.progress)

        self.apply_styles()

        # Подключаем сигналы
        self.generate_btn.clicked.connect(self.on_generate)
        self.download_btn.clicked.connect(self.on_download)

    # ==================== DRAG & DROP ====================
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Срабатывает, когда файлы перетаскиваются в окно."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Разрешаем перемещение."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Обрабатываем сброс файлов."""
        urls = event.mimeData().urls()
        if not urls:
            return

        # Проверяем, что файлы можно обработать
        for url in urls:
            file_path = url.toLocalFile()
            if not file_path:
                continue
            if self._add_file(file_path):
                event.acceptProposedAction()
            else:
                # Если файл не добавился, показываем ошибку в статусе
                self.status_label.setText(f"Ошибка: {Path(file_path).name} не добавлен")
                event.ignore()

    def _add_file(self, file_path: str) -> bool:
        """Добавляет файл в список, если это возможно."""
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

    # ==================== ОБНОВЛЕНИЕ СПИСКА ФАЙЛОВ ====================
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

    # ==================== КОНТЕКСТНОЕ МЕНЮ ДЛЯ УДАЛЕНИЯ ФАЙЛОВ ====================
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
        if current_row >= 0 and current_row < len(self.attached_files):
            del self.attached_files[current_row]
            self._update_files_list()
            self.status_label.setText("Файл удалён")

    # ==================== ОБЫЧНЫЙ ДИАЛОГ ВЫБОРА ФАЙЛА (СВЕТЛЫЙ) ====================
    def on_attach_file(self):
        if len(self.attached_files) >= self.MAX_FILES:
            self.status_label.setText(f"Максимум {self.MAX_FILES} файлов!")
            return

        # Создаём диалог с явной светлой палитрой, чтобы текст был виден
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Выберите файлы")
        dialog.setDirectory(str(Path.home() / "Desktop"))
        dialog.setNameFilter("Поддерживаемые файлы (*.txt *.pdf *.docx);;PDF файлы (*.pdf);;Word документы (*.docx);;Текстовые файлы (*.txt);;Все файлы (*.*)")
        dialog.setFileMode(QFileDialog.ExistingFiles)

        # Принудительно задаём палитру с белым фоном и чёрным текстом для диалога
        light_palette = QPalette()
        light_palette.setColor(QPalette.Window, Qt.white)
        light_palette.setColor(QPalette.WindowText, Qt.black)
        light_palette.setColor(QPalette.Base, Qt.white)
        light_palette.setColor(QPalette.Text, Qt.black)
        light_palette.setColor(QPalette.Button, Qt.lightGray)
        light_palette.setColor(QPalette.ButtonText, Qt.black)
        dialog.setPalette(light_palette)

        # Запускаем диалог
        if dialog.exec_() == QFileDialog.Accepted:
            file_paths = dialog.selectedFiles()
            for file_path in file_paths:
                self._add_file(file_path)

    # ==================== СТИЛИ ====================
    def apply_styles(self):
        style = """
            QMainWindow { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0f0f23, stop:1 #1a1a3e);
            }
            QLabel { 
                color: #e0e6ff;
            }
            QTextEdit {
                background-color: #16172e;
                color: #b8c5ff;
                border: 1px solid #2d2f5e;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Courier New';
            }
            QWidget {
                background-color: transparent;
            }
            QFrame {
                background-color: #16172e;
                border: 1px solid #2d2f5e;
                border-radius: 8px;
            }
            QListWidget {
                background-color: #16172e;
                color: #b8c5ff;
                border: 1px solid #2d2f5e;
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
                margin: 2px 0px;
            }
            QListWidget::item:hover {
                background-color: #2a2d5a;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #3d4080;
                border-radius: 4px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b9eff, stop:1 #5b8ff0);
                color: #0a0a14;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7badff, stop:1 #6b9eff);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5b8ff0, stop:1 #4b7fe8);
            }
            QPushButton:disabled { 
                background-color: #3d3f5a;
                color: #7a7d94;
            }
            QTabWidget::pane { 
                border: 1px solid #2d2f5e;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #1a1c3e;
                color: #b8c5ff;
                padding: 6px 16px;
                margin: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2d2f5e;
                color: #e0e6ff;
            }
            QProgressBar {
                background-color: #1a1c3e;
                border: 1px solid #2d2f5e;
                border-radius: 6px;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b9eff, stop:1 #7badff);
                border-radius: 4px;
            }
            QSplitter::handle { 
                background-color: #2d2f5e;
                width: 10px;
                margin: 0px 4px;
                border-radius: 5px;
            }
            QSplitter::handle:hover { 
                background-color: #3d4080;
            }
            QMenu {
                background-color: #1a1c3e;
                color: #e0e6ff;
                border: 1px solid #2d2f5e;
            }
            QMenu::item:selected {
                background-color: #3d4080;
            }
        """
        self.setStyleSheet(style)

    # ==================== ГЕНЕРАЦИЯ ====================
    def on_generate(self):
        manual_text = self.input_text.toPlainText().strip()

        file_texts = []
        for file_path in self.attached_files:
            text = extract_text_from_file(file_path)
            if text and not text.startswith("Ошибка"):
                file_texts.append(text)
            elif text and text.startswith("Ошибка"):
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

        modules_dir = Path(__file__).parent / "modules"
        for module_file in sorted(modules_dir.glob("*.py")):
            editor = QTextEdit()
            editor.setReadOnly(True)
            editor.setFont(QFont("Courier New", 12))
            editor.setText(module_file.read_text(encoding="utf-8"))
            self.tabs.addTab(editor, module_file.name)

        # Показываем итоговый лог во вкладке (опционально)
        log_tab = QTextEdit()
        log_tab.setReadOnly(True)
        log_tab.setFont(QFont("Courier New", 12))
        log_tab.setText(log)
        # self.tabs.addTab(log_tab, "Лог (итоговый)")  # раскомментируйте, если нужен

        self._clear_attached_files()

    def on_download(self):
        target_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения проекта")
        if not target_dir:
            return

        modules_dir = Path(__file__).parent / "modules"
        manifest_file = Path(__file__).parent / "manifest.json"

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