import subprocess
import tempfile
import os

class DockerRunner:
    def __init__(self, image="python:3.10-slim", timeout=30, memory="256m"):
        self.image = image
        self.timeout = timeout
        self.memory = memory

    def run_code(self, code: str):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".py")
        tmp.write(code.encode("utf-8"))
        tmp.close()

        return self.run(tmp.name)

    def run(self, file_path: str):
        cmd = [
            "docker", "run", "--rm",
            "-m", self.memory,
            "-v", f"{file_path}:/app/code.py",
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
            os.unlink(file_path)
            return result.stdout, result.stderr
        except Exception as e:
            os.unlink(file_path)
            return "", str(e)
