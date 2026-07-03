import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QSplitter, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from .agent import CodeAgent

class Worker(QThread):
    finished = pyqtSignal(str, str)

    def __init__(self, tech_task):
        super().__init__()
        self.tech_task = tech_task

    def run(self):
        agent = CodeAgent()
        result = agent.run(self.tech_task)
        self.finished.emit(result['code'], result['log'])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ИИ-агент для генерации кода")
        self.setMinimumSize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Генерация кода по техническому заданию")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        main_layout.addWidget(title)

        input_label = QLabel("Техническое задание:")
        input_label.setFont(QFont("Arial", 13, QFont.Bold))
        main_layout.addWidget(input_label)

        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Courier New", 12))
        self.input_text.setMinimumHeight(250)
        main_layout.addWidget(self.input_text)

        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Сгенерировать код")
        self.generate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        btn_layout.addWidget(self.generate_btn)

        self.status_label = QLabel("Готов")
        self.status_label.setFont(QFont("Arial", 11))
        btn_layout.addWidget(self.status_label)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        output_label = QLabel("Результат генерации:")
        output_label.setFont(QFont("Arial", 13, QFont.Bold))
        main_layout.addWidget(output_label)

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(6)
        main_layout.addWidget(splitter)

        output_splitter = QSplitter(Qt.Horizontal)
        output_splitter.setHandleWidth(6)

        code_container = QWidget()
        code_container.setMinimumHeight(300)
        code_container.setMinimumWidth(450)
        code_layout = QVBoxLayout(code_container)

        code_label = QLabel("Код:")
        code_label.setFont(QFont("Arial", 12, QFont.Bold))
        code_layout.addWidget(code_label)

        self.code_output = QTextEdit()
        self.code_output.setFont(QFont("Courier New", 12))
        self.code_output.setReadOnly(True)
        self.code_output.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        code_layout.addWidget(self.code_output)

        log_container = QWidget()
        log_container.setMinimumHeight(300)
        log_container.setMinimumWidth(350)
        log_layout = QVBoxLayout(log_container)

        log_label = QLabel("Лог выполнения:")
        log_label.setFont(QFont("Arial", 12, QFont.Bold))
        log_layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setFont(QFont("Courier New", 12))
        self.log_output.setReadOnly(True)
        self.log_output.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        log_layout.addWidget(self.log_output)

        output_splitter.addWidget(code_container)
        output_splitter.addWidget(log_container)
        output_splitter.setSizes([750, 450])

        splitter.addWidget(output_splitter)
        splitter.setSizes([400, 400])

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(8)
        main_layout.addWidget(self.progress)

        self.apply_styles()
        self.generate_btn.clicked.connect(self.on_generate)

    def apply_styles(self):
        style = """
            QMainWindow { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QTextEdit {
                background-color: #1a1b26;
                color: #a6adc8;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #74c7ec; }
            QPushButton:disabled { background-color: #45475a; color: #a6adc8; }
            QSplitter::handle { background-color: #313244; }
        """
        self.setStyleSheet(style)

    def on_generate(self):
        tech_task = self.input_text.toPlainText().strip()
        if not tech_task:
            self.status_label.setText("Введите ТЗ!")
            return

        self.generate_btn.setEnabled(False)
        self.status_label.setText("Генерация...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.code_output.clear()
        self.log_output.clear()

        self.worker = Worker(tech_task)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, code, log):
        self.code_output.setText(code)
        self.log_output.setText(log)
        self.generate_btn.setEnabled(True)
        self.status_label.setText("Готово")
        self.progress.setVisible(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 12))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
