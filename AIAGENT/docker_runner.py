import subprocess
import tempfile
import shutil
from pathlib import Path


class DockerRunner:
    def __init__(self, image="python:3.10-slim", timeout=30, memory="256m"):
        self.image = image
        self.timeout = timeout
        self.memory = memory

    def run_code(self, code: str):
        """
        Запуск одиночного модуля в Docker.
        Используется для проверки обычных модулей (не main.py).
        """
        tmpdir = Path(tempfile.mkdtemp())
        code_file = tmpdir / "code.py"
        code_file.write_text(code, encoding="utf-8")

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
