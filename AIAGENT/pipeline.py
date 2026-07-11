# pipeline.py

from pathlib import Path
import json
import ast
import re
import sys
import traceback
from .prompt_builder import build_module_prompt
from .module_analyzer import ModuleAnalyzer

STANDARD_LIBS = {
    "math", "os", "sys", "re", "json", "random", "datetime",
    "collections", "itertools", "functools", "typing", "abc",
    "io", "pathlib", "statistics", "decimal", "fractions",
    "time", "logging", "unittest", "subprocess", "tempfile",
    "shutil", "hashlib", "base64", "csv", "xml", "html",
    "urllib", "http", "socket", "select", "threading",
    "multiprocessing", "asyncio", "inspect", "textwrap",
    "string", "pprint", "copy", "weakref", "warnings"
}

VARIABLE_LIKE_NAMES = {
    "file_path", "file", "data", "result", "item", "value", "self", "cls",
    "path", "filename", "text", "content", "line", "row", "column"
}


def get_base_dir():
    """Определение базовой директории исполняемого приложения или скрипта."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


class Pipeline:
    """
    Оркестратор генерации, валидации и выполнения Python-модулей на основе технического задания.
    """

    def __init__(self, generator, validator, docker):
        """
        Инициализация конвейера с компонентами генерации, валидации и выполнения в Docker.
        """
        self.generator = generator
        self.validator = validator
        self.docker = docker
        self.analyzer = ModuleAnalyzer()
        base_dir = get_base_dir()
        self.modules_dir = base_dir / "modules"
        self.modules_dir.mkdir(exist_ok=True)

    def _extract_interfaces(self, code: str, module_name: str):
        """
        Извлечение интерфейсов (классов и их методов) из кода модуля.
        """
        interfaces = {}
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return interfaces

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                methods = {}
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        params = [arg.arg for arg in item.args.args]
                        signature = f"def {item.name}({', '.join(params)})"
                        methods[item.name] = signature

                interfaces[class_name] = {
                    "module": module_name,
                    "methods": methods
                }

        return interfaces

    def _get_module_dependencies(self, module: dict) -> list:
        """Список зависимостей модуля из его описания."""
        return module.get("depends_on", [])

    def _generate_module(self, tech_task, manifest, module, interfaces, all_codes, log_msg):
        """
        Генерация кода отдельного модуля с циклической проверкой и устранением дублей.
        """
        name = module["name"]
        log_msg(f"Генерация модуля: {name}")

        try:
            existing_code = "\n\n".join([
                f"# {filename}\n{code}"
                for filename, code in all_codes.items()
                if filename != f"{name}.py"
            ])

            prompt = build_module_prompt(
                tech_task=tech_task,
                manifest=manifest,
                module=module,
                interfaces=json.dumps(interfaces, indent=4, ensure_ascii=False),
                all_modules_code=existing_code
            )

            log_msg(f"{name}: отправляю запрос к Ollama")
            code = self.generator.generate_code(prompt)
            log_msg(f"{name}: код сгенерирован (длина {len(code)})")

            iteration_limit = 20
            for iteration in range(1, iteration_limit):
                ok, err = self.validator.validate(code)
                if not ok:
                    log_msg(f"{name}: синтаксическая ошибка → перегенерация ({iteration})")
                    code = self.generator.generate_code(
                        prompt + f"\nИсправь синтаксическую ошибку:\n{err}\nТвой предыдущий код:\n{code}"
                    )
                    continue

                new_ifaces = self._extract_interfaces(code, name)
                duplicated = set(new_ifaces.keys()) & set(interfaces.keys())
                if duplicated:
                    log_msg(f"{name}: предупреждение – дубли классов {', '.join(duplicated)} (удаляем)")
                    for cls in duplicated:
                        pattern = rf'class {cls}\s*:.*?(?=\nclass |\Z)'
                        code = re.sub(pattern, '', code, flags=re.DOTALL)
                    log_msg(f"{name}: дубли удалены")
                    ok2, err2 = self.validator.validate(code)
                    if ok2:
                        log_msg(f"{name}: синтаксис ОК (после удаления дублей)")
                        break
                    else:
                        log_msg(f"{name}: синтаксическая ошибка после удаления дублей → перегенерация")
                        code = self.generator.generate_code(
                            prompt + f"\nИсправь синтаксическую ошибку:\n{err2}\nТвой предыдущий код:\n{code}"
                        )
                        continue

                log_msg(f"{name}: синтаксис ОК")
                break

            (self.modules_dir / f"{name}.py").write_text(code, encoding="utf-8")
            interfaces.update(self._extract_interfaces(code, name))
            all_codes[f"{name}.py"] = code
            log_msg(f"{name}: модуль сохранён")

        except Exception as e:
            log_msg(f"Ошибка при генерации модуля {name}: {e}")
            traceback.print_exc()
            raise

    def _generate_main(self, tech_task, manifest, interfaces, all_codes, log_msg):
        """
        Генерация главного модуля main.py как точки входа.
        """
        name = "main"
        log_msg("Генерация главного модуля: main")

        try:
            existing_code = "\n\n".join([
                f"# {filename}\n{code}"
                for filename, code in all_codes.items()
                if filename != "main.py"
            ])

            prompt = f"""
Ты — ИИ-агент, который пишет главный модуль Python-проекта.

main.py — ЕДИНСТВЕННАЯ точка входа.

СТРОГИЕ ПРАВИЛА:
- main.py НЕ должен содержать бизнес-логику.
- main.py НЕ должен дублировать код других модулей.
- main.py должен использовать ТОЛЬКО методы, перечисленные в интерфейсах.
- main.py должен импортировать все модули: {list(interfaces.keys())}
- main.py должен создавать объекты классов и вызывать их методы.
- main.py должен содержать функцию main().
- main.py НЕ должен содержать определения классов.
- main.py НЕ должен содержать определения функций, кроме main().
- НЕ используй неопределённые переменные. Передавай все параметры явно.

ИНТЕРФЕЙСЫ:
{json.dumps(interfaces, indent=4, ensure_ascii=False)}

Техническое задание:
{tech_task}

Сгенерируй ТОЛЬКО main.py.
"""

            code = self.generator.generate_code(prompt)
            log_msg("main: код сгенерирован")

            for iteration in range(1, 4):
                ok, err = self.validator.validate(code)
                if not ok:
                    log_msg(f"main: синтаксическая ошибка → перегенерация ({iteration})")
                    code = self.generator.generate_code(
                        prompt + f"\nИсправь синтаксическую ошибку:\n{err}\nТвой предыдущий код:\n{code}"
                    )
                    continue
                log_msg("main: синтаксис ОК")
                break

            (self.modules_dir / "main.py").write_text(code, encoding="utf-8")
            all_codes["main.py"] = code
            log_msg("main: модуль сохранён")

        except Exception as e:
            log_msg(f"Ошибка при генерации main: {e}")
            traceback.print_exc()
            raise

    def _remove_empty_modules(self, log_msg):
        """
        Удаление файлов модулей, не содержащих классов или функций.
        """
        removed = []
        for py_file in self.modules_dir.glob("*.py"):
            if py_file.name == "main.py":
                continue
            content = py_file.read_text(encoding="utf-8")
            has_class = re.search(r'^\s*class\s+\w+', content, re.MULTILINE)
            has_function = re.search(r'^\s*def\s+\w+', content, re.MULTILINE)
            if not has_class and not has_function:
                py_file.unlink()
                removed.append(py_file.name)
                log_msg(f"🗑️ Удалён пустой модуль (нет классов/функций): {py_file.name}")
        return removed

    def _extract_error_modules(self, stderr: str) -> list:
        """Извлечение имён файлов модулей из текста ошибки выполнения."""
        matches = re.findall(r'File ".*?([^/\\]+\.py)"', stderr)
        return [m.rsplit('.', 1)[0] for m in matches]

    def _extract_missing_names(self, stderr: str) -> list:
        """Извлечение неопределённых имён (NameError) из текста ошибки."""
        matches = re.findall(r"name '(\w+)' is not defined", stderr)
        return matches

    def _extract_import_names(self, stderr: str) -> list:
        """Извлечение имён, которые не удаётся импортировать, из текста ошибки."""
        matches = re.findall(r"cannot import name '(\w+)'", stderr)
        return matches

    def _extract_module_from_import_error(self, stderr: str) -> str:
        """Извлечение имени модуля из сообщения об ошибке импорта."""
        match = re.search(r"from '(\w+)'", stderr)
        if match:
            return match.group(1)
        return None

    def _get_imports(self, code: str) -> list:
        """Список строк импорта из кода."""
        imports = []
        for line in code.splitlines():
            line = line.strip()
            if line.startswith(('import ', 'from ')):
                imports.append(line)
        return imports

    def _get_defined_classes(self, code: str) -> list:
        """Список имён классов, определённых в коде."""
        classes = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
        except SyntaxError:
            pass
        return classes

    def _get_defined_functions(self, code: str) -> list:
        """Список имён функций, определённых в коде."""
        funcs = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    funcs.append(node.name)
        except SyntaxError:
            pass
        return funcs

    def _module_contains(self, code: str, name: str) -> bool:
        """Проверка, содержит ли код класс или функцию с заданным именем."""
        return name in self._get_defined_classes(code) or name in self._get_defined_functions(code)

    def _find_module_for_import(self, all_codes, import_name):
        """Поиск модуля, в котором определён класс или функция с указанным именем."""
        for filename, code in all_codes.items():
            if self._module_contains(code, import_name):
                return filename.replace(".py", "")
        return None

    def _add_missing_module(self, tech_task, manifest, module_name, log_msg):
        """
        Добавление недостающего модуля в манифест, если он не является стандартной библиотекой или переменной.
        """
        if module_name.lower() in VARIABLE_LIKE_NAMES:
            log_msg(f"{module_name} похоже на переменную, не создаём модуль")
            return False

        norm = module_name.replace('.py', '').strip()
        norm = re.sub(r'[^a-zA-Z0-9_]', '', norm)
        norm = re.sub(r'([A-Z]+)', lambda m: '_' + m.group(1).lower(), norm).lstrip('_').lower()

        if norm in STANDARD_LIBS:
            log_msg(f"{module_name} — стандартная библиотека, не создаём модуль")
            return False

        if module_name and module_name[0].isupper():
            log_msg(f"{module_name} похоже на имя класса, не создаём модуль")
            return False

        if not any(m["name"] == norm for m in manifest["modules"]):
            log_msg(f"Добавляем недостающий модуль: {norm}")
            manifest["modules"].append({
                "name": norm,
                "description": f"модуль для {module_name}",
                "depends_on": []
            })
            return True
        log_msg(f"Модуль {module_name} уже присутствует, пропускаем")
        return False

    def _regenerate_module(self, tech_task, manifest, module, interfaces, all_codes, log_msg, error_msg, extra_info=""):
        """
        Перегенерация модуля с учётом ошибок выполнения, с добавлением информации об ошибке в промпт.
        """
        name = module["name"]
        log_msg(f"Перегенерация модуля {name} с учётом ошибок")

        try:
            existing_code = "\n\n".join([
                f"# {filename}\n{code}"
                for filename, code in all_codes.items()
                if filename != f"{name}.py"
            ])

            prompt = build_module_prompt(
                tech_task=tech_task,
                manifest=manifest,
                module=module,
                interfaces=json.dumps(interfaces, indent=4, ensure_ascii=False),
                all_modules_code=existing_code
            ) + f"\n\nОШИБКА ПРИ ЗАПУСКЕ ПРОЕКТА:\n{error_msg}\n{extra_info}\n\nИсправь код модуля {name} с учётом этой ошибки. Проверь импорты. Используй абсолютные импорты."

            code = self.generator.generate_code(prompt)
            log_msg(f"{name}: перегенерирован код")

            ok, err = self.validator.validate(code)
            if not ok:
                log_msg(f"{name}: синтаксическая ошибка в новом коде, оставляем старый")
                return

            (self.modules_dir / f"{name}.py").write_text(code, encoding="utf-8")
            interfaces.update(self._extract_interfaces(code, name))
            all_codes[f"{name}.py"] = code
            log_msg(f"{name}: обновлён")

        except Exception as e:
            log_msg(f"Ошибка при перегенерации {name}: {e}")
            traceback.print_exc()
            raise

    def _regenerate_main(self, tech_task, manifest, interfaces, all_codes, log_msg, error_msg, extra_info=""):
        """
        Перегенерация main.py с учётом ошибок выполнения.
        """
        log_msg("Перегенерация main с учётом ошибок")

        try:
            existing_code = "\n\n".join([
                f"# {filename}\n{code}"
                for filename, code in all_codes.items()
                if filename != "main.py"
            ])

            prompt = f"""
Ты — ИИ-агент, который пишет главный модуль Python-проекта.

main.py — ЕДИНСТВЕННАЯ точка входа.
main.py МОЖЕТ использовать print().

СТРОГИЕ ПРАВИЛА:
- main.py НЕ должен содержать бизнес-логику.
- main.py НЕ должен дублировать код других модулей.
- main.py должен использовать ТОЛЬКО методы, перечисленные в интерфейсах.
- main.py должен импортировать все модули: {list(interfaces.keys())}
- main.py должен создавать объекты классов и вызывать их методы.
- main.py должен содержать функцию main().
- НЕ используй неопределённые переменные. Передавай все параметры явно.

Код уже сгенерированных модулей:
{existing_code}

ИНТЕРФЕЙСЫ:
{json.dumps(interfaces, indent=4, ensure_ascii=False)}

Техническое задание:
{tech_task}

ОШИБКА ПРИ ЗАПУСКЕ ПРОЕКТА:
{error_msg}
{extra_info}

Исправь main.py с учётом этой ошибки. Проверь импорты. Используй абсолютные импорты.
"""

            code = self.generator.generate_code(prompt)
            log_msg("main: перегенерирован код")

            ok, err = self.validator.validate(code)
            if not ok:
                log_msg("main: синтаксическая ошибка в новом коде, оставляем старый")
                return

            (self.modules_dir / "main.py").write_text(code, encoding="utf-8")
            all_codes["main.py"] = code
            log_msg("main: обновлён")

        except Exception as e:
            log_msg(f"Ошибка при перегенерации main: {e}")
            traceback.print_exc()
            raise

    def _fix_imports_in_file(self, filename: str, all_codes: dict, interfaces: dict, log_msg):
        """
        Исправление импортов в файле: замена неверного модуля-источника на тот, где определён импортируемый объект.
        """
        if filename not in all_codes:
            return
        code = all_codes[filename]
        imports = self._get_imports(code)
        changed = False
        for imp in imports:
            if imp.startswith('from '):
                parts = imp.split()
                if len(parts) >= 4:
                    from_module = parts[1]
                    import_names = parts[3].split(',')
                    for name in import_names:
                        name = name.strip()
                        target_module = self._find_module_for_import(all_codes, name)
                        if target_module and target_module != from_module:
                            log_msg(f"Исправляем импорт {name} в {filename}: {from_module} -> {target_module}")
                            new_imp = f"from {target_module} import {name}"
                            code = code.replace(imp, new_imp)
                            changed = True
        if changed:
            all_codes[filename] = code
            (self.modules_dir / filename).write_text(code, encoding="utf-8")
            interfaces.update(self._extract_interfaces(code, filename.replace(".py", "")))
            log_msg(f"Исправлены импорты в {filename}")

    def _run_project_and_fix(self, tech_task, manifest, interfaces, all_codes, log_msg, max_attempts=3):
        """
        Запуск проекта в Docker и итеративное исправление ошибок путём перегенерации модулей.
        """
        for attempt in range(1, max_attempts + 1):
            log_msg(f"Запуск проекта (попытка {attempt})")
            stdout, stderr = self.docker.run_project(self.modules_dir)

            if not stderr:
                log_msg("Проект успешно выполнен без ошибок!")
                return True, stdout

            log_msg(f"Ошибка выполнения проекта:\n{stderr}")

            try:
                if "partially initialized module" in stderr:
                    module_names = self._extract_error_modules(stderr)
                    for mod in module_names:
                        if mod != "main":
                            log_msg(f"Обнаружен циклический импорт в модуле {mod}")
                            module = next((m for m in manifest["modules"] if m["name"] == mod), None)
                            if module:
                                self._regenerate_module(tech_task, manifest, module, interfaces, all_codes, log_msg, stderr,
                                                        "\nИЗБЕГАЙ циклических импортов. Используй абсолютные импорты.")
                    continue

                missing_modules = re.findall(r"No module named '(\w+)'", stderr)
                for mod in missing_modules:
                    if self._add_missing_module(tech_task, manifest, mod, log_msg):
                        module = {"name": mod, "description": f"модуль для {mod}", "depends_on": []}
                        self._generate_module(tech_task, manifest, module, interfaces, all_codes, log_msg)

                import_names = self._extract_import_names(stderr)
                from_module = self._extract_module_from_import_error(stderr)

                if import_names and from_module:
                    for name in import_names:
                        target_module = self._find_module_for_import(all_codes, name)

                        if target_module and target_module != from_module:
                            log_msg(f"Класс {name} определён в {target_module}, а импортируется из {from_module}")
                            for mod_name in all_codes.keys():
                                self._fix_imports_in_file(mod_name, all_codes, interfaces, log_msg)

                        elif not target_module:
                            log_msg(f"Класс {name} нигде не определён, создаём модуль {name.lower()}")
                            self._add_missing_module(tech_task, manifest, name.lower(), log_msg)
                            module = {"name": name.lower(), "description": f"класс {name}", "depends_on": []}
                            self._generate_module(tech_task, manifest, module, interfaces, all_codes, log_msg)

                missing_classes = self._extract_missing_names(stderr)
                for cls in missing_classes:
                    if cls in STANDARD_LIBS:
                        log_msg(f"{cls} — стандартная библиотека, добавляем import")
                        for mod_name in self._extract_error_modules(stderr):
                            if mod_name == "main":
                                self._regenerate_main(tech_task, manifest, interfaces, all_codes, log_msg,
                                                     f"{stderr}\n\nДобавь 'import {cls}' в начало файла.")
                            else:
                                module = next((m for m in manifest["modules"] if m["name"] == mod_name), None)
                                if module:
                                    self._regenerate_module(tech_task, manifest, module, interfaces, all_codes, log_msg,
                                                           f"{stderr}\n\nДобавь 'import {cls}' в начало файла.")
                        continue

                    if cls in VARIABLE_LIKE_NAMES:
                        log_msg(f"{cls} похоже на переменную, не создаём модуль")
                        for mod_name in self._extract_error_modules(stderr):
                            if mod_name == "main":
                                self._regenerate_main(tech_task, manifest, interfaces, all_codes, log_msg,
                                                     f"{stderr}\n\nНе используй неопределённую переменную '{cls}'. Передавай все параметры явно.")
                            else:
                                module = next((m for m in manifest["modules"] if m["name"] == mod_name), None)
                                if module:
                                    self._regenerate_module(tech_task, manifest, module, interfaces, all_codes, log_msg,
                                                           f"{stderr}\n\nНе используй неопределённую переменную '{cls}'. Передавай все параметры явно.")
                        continue

                    existing_module = self._find_module_for_import(all_codes, cls)
                    if existing_module:
                        log_msg(f"Класс {cls} найден в {existing_module}, добавляем импорт")
                        self._regenerate_main(tech_task, manifest, interfaces, all_codes, log_msg, stderr,
                                             f"\nДобавь импорт 'from {existing_module} import {cls}' в main.py")
                        for mod in manifest["modules"]:
                            if mod["name"] != "main":
                                self._regenerate_module(tech_task, manifest, mod, interfaces, all_codes, log_msg, stderr,
                                                       f"\nДобавь импорт 'from {existing_module} import {cls}' в {mod['name']}.")
                    else:
                        if len(cls) > 2 and not cls.islower():
                            log_msg(f"Класс {cls} не найден, создаём модуль {cls.lower()}")
                            self._add_missing_module(tech_task, manifest, cls.lower(), log_msg)
                            module = {"name": cls.lower(), "description": f"класс {cls}", "depends_on": []}
                            self._generate_module(tech_task, manifest, module, interfaces, all_codes, log_msg)
                        else:
                            log_msg(f"Игнорируем неопределённое имя '{cls}' – скорее всего, переменная")

                module_names = self._extract_error_modules(stderr)
                for name in module_names:
                    if name == "main":
                        self._regenerate_main(tech_task, manifest, interfaces, all_codes, log_msg, stderr)
                    else:
                        module = next((m for m in manifest["modules"] if m["name"] == name), None)
                        if module:
                            self._regenerate_module(tech_task, manifest, module, interfaces, all_codes, log_msg, stderr)

                for mod_name in all_codes.keys():
                    self._fix_imports_in_file(mod_name, all_codes, interfaces, log_msg)

                for mod_name, code in all_codes.items():
                    module_name = mod_name.replace(".py", "")
                    interfaces.update(self._extract_interfaces(code, module_name))

            except Exception as e:
                log_msg(f"Ошибка в _run_project_and_fix на попытке {attempt}: {e}")
                traceback.print_exc()
                return False, str(e)

        log_msg("Не удалось исправить ошибки после всех попыток")
        return False, stderr

    def run(self, tech_task: str, callback=None):
        """
        Запуск полного конвейера: анализ, генерация модулей, выполнение и итеративное исправление.
        """
        log = []
        interfaces = {}
        all_codes = {}

        for f in self.modules_dir.glob("*.py"):
            f.unlink()

        def log_msg(msg: str):
            log.append(msg)
            if callback:
                callback(msg)

        try:
            manifest = self.analyzer.analyze(tech_task)
            log_msg("Анализ архитектуры и модулей выполнен")

            modules = [m for m in manifest["modules"] if m["name"] != "main"]
            modules.sort(key=lambda m: (len(self._get_module_dependencies(m)), m["name"]))

            for module in modules:
                self._generate_module(tech_task, manifest, module, interfaces, all_codes, log_msg)

            self._generate_main(tech_task, manifest, interfaces, all_codes, log_msg)

            removed = self._remove_empty_modules(log_msg)
            if removed:
                manifest["modules"] = [
                    m for m in manifest["modules"]
                    if m["name"] != "main" and f"{m['name']}.py" not in removed
                ] + [m for m in manifest["modules"] if m["name"] == "main"]

            success, output = self._run_project_and_fix(tech_task, manifest, interfaces, all_codes, log_msg)

            base_dir = get_base_dir()
            (base_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )

            return {
                "manifest": manifest,
                "log": "\n".join(log),
                "project_success": success,
                "project_output": output
            }

        except Exception as e:
            log_msg(f"Критическая ошибка в Pipeline.run: {e}")
            traceback.print_exc()
            return {
                "manifest": {},
                "log": "\n".join(log),
                "project_success": False,
                "project_output": str(e)
            }