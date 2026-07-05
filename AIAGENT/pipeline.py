from .prompt_builder import build_prompt

class Pipeline:
    def __init__(self, generator, validator, docker):
        self.generator = generator
        self.validator = validator
        self.docker = docker

    def run(self, tech_task: str):
        log = []
 
        prompt = build_prompt(tech_task)
 
        code = self.generator.generate_code(prompt)
        log.append("Итерация 1: сгенерирован код")

        for iteration in range(1, 4):
            log.append(f"Итерация {iteration}: проверка синтаксиса")
            ok, err = self.validator.validate(code)

            if not ok:
                log.append(f"Итерация {iteration}: синтаксическая ошибка → перегенерация")
                code = self.generator.generate_code(
                    build_prompt(tech_task)
                    + f"\nИсправь синтаксическую ошибку:\n{err}\nТвой предыдущий код:\n{code}"
                )
                continue

            log.append(f"Итерация {iteration}: запуск в Docker")
            stdout, stderr = self.docker.run_code(code)

            log.append(f"stdout:\n{stdout}")
            log.append(f"stderr:\n{stderr}")

            if not stderr:
                log.append(f"Итерация {iteration}: код успешно исполнился")
                return code, "\n".join(log)

            log.append(f"Итерация {iteration}: ошибка выполнения → перегенерация")
            code = self.generator.generate_code(
                build_prompt(tech_task)
                + f"\nИсправь ошибку выполнения:\n{stderr}\nТвой предыдущий код:\n{code}"
            )

        log.append("Итог: код не стал исполняемым после 3 итераций")
        return code, "\n".join(log)
