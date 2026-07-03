from . import generator, validator, parser

class CodeAgent:
    def __init__(self):
        self.history = []

    def run(self, tech_task: str):
        """Main loop: generate code and validate syntax."""
        tests = parser.extract_tests(tech_task)
        prompt = f"""
        Write Python code for the task:
        {tech_task}

        If the task contains tests (assert), ensure the code passes them.
        Return only the code without explanations.
        """
        code = generator.generate_code(prompt)
        if code is None:
            return {"success": False, "code": "", "log": "Generation error", "iterations": 0}
        self.history.append(code)
        ok, msg = validator.validate_syntax(code)
        if not ok:
            return {"success": False, "code": code, "log": msg, "iterations": 1}
        return {"success": True, "code": code, "log": "Syntax OK", "iterations": 1}