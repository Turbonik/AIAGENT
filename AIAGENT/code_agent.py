from .pipeline import Pipeline
from .docker_runner import DockerRunner
from .syntax_validator import validate_syntax
from .generator import CodeGenerator

class CodeAgent:
    def __init__(self):
        self.pipeline = Pipeline(
            generator=CodeGenerator(),
            validator=type("V", (), {"validate": validate_syntax}),
            docker=DockerRunner()
        )

    def run(self, tech_task: str, callback=None):
        return self.pipeline.run(tech_task, callback)
