import subprocess
import tempfile
import shutil
import re
import csv
from pathlib import Path


class DockerRunner:
    """Запускает Python код в контейнере Docker с поддержкой автоматического создания data файлов."""
    
    def __init__(self, image="python:3.10-slim", timeout=30, memory="256m"):
        self.image = image
        self.timeout = timeout
        self.memory = memory
        self.data_extensions = {'.csv', '.txt', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg'}
    
    def _extract_file_references(self, code: str) -> set:
        """
        Извлекает все ссылки на файлы данных из кода.
        """
        files = set()
        
        patterns = [
            r'["\']([a-zA-Z0-9_\-./\\]*\.(?:csv|txt|json|xml|yaml|yml|toml|ini|cfg))["\']',
            r'(?:open|read|load|write)\s*\(\s*["\']([a-zA-Z0-9_\-./\\]*\.(?:csv|txt|json|xml|yaml|yml|toml|ini|cfg))["\']',
            r'(?:Path|pathlib)[^)]*["\']([a-zA-Z0-9_\-./\\]*\.(?:csv|txt|json|xml|yaml|yml|toml|ini|cfg))["\']',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                filename = match.group(1)
                filename = Path(filename).name
                if filename and not filename.startswith('.'):
                    files.add(filename)
        
        return files
    
    def _create_stub_file(self, filepath: Path) -> None:
        """
        Создаёт stub-файл данных в зависимости от расширения.
        """
        ext = filepath.suffix.lower()
        
        try:
            if ext == '.csv':
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['id', 'name', 'value'])
                    writer.writerow(['1', 'sample', '100'])
            
            elif ext == '.json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('{"data": [], "status": "ok"}')
            
            elif ext in {'.yaml', '.yml'}:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('data: []\nstatus: ok\n')
            
            elif ext == '.xml':
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('<?xml version="1.0" encoding="utf-8"?>\n<root><data/></root>')
            
            elif ext in {'.toml', '.ini', '.cfg'}:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('[DEFAULT]\nstatus=ok\ndata=\n')
            
            else:
                filepath.touch()
        
        except Exception as e:
            filepath.touch()
    
    def _create_data_files(self, tmpdir: Path, code: str) -> None:
        """
        Создаёт все необходимые stub-файлы данных для кода.       
        """
        file_references = self._extract_file_references(code)
        
        for filename in file_references:
            filepath = tmpdir / filename

            if not filepath.exists():
                self._create_stub_file(filepath)

    def run_code(self, code: str):
        """
        Запуск одиночного модуля в Docker.
        """
        tmpdir = Path(tempfile.mkdtemp())
        code_file = tmpdir / "code.py"
        code_file.write_text(code, encoding="utf-8")

        self._create_data_files(tmpdir, code)

        cmd = [
            "docker", "run", "--rm",
            "-m", self.memory,
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{tmpdir}:/app",
            self.image,
            "python", "/app/code.py"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            shutil.rmtree(tmpdir, ignore_errors=True)
            return result.stdout, result.stderr
        except Exception as e:
            shutil.rmtree(tmpdir, ignore_errors=True)
            return "", str(e)

    def run_project(self, modules_dir: Path, entrypoint: str = "main.py"):
        """
        Запуск всего проекта в Docker.
        Используется только для main.py.
        """
        tmpdir = Path(tempfile.mkdtemp())
        shutil.copytree(modules_dir, tmpdir, dirs_exist_ok=True)

        for py_file in tmpdir.glob("**/*.py"):
            try:
                code = py_file.read_text(encoding="utf-8")
                self._create_data_files(tmpdir, code)
            except Exception:
                pass

        cmd = [
            "docker", "run", "--rm",
            "-m", self.memory,
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{tmpdir}:/app",
            self.image,
            "python", f"/app/{entrypoint}"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            shutil.rmtree(tmpdir, ignore_errors=True)
            return result.stdout, result.stderr
        except Exception as e:
            shutil.rmtree(tmpdir, ignore_errors=True)
            return "", str(e)
