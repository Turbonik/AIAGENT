import json
import re
import requests
from . import config

class ModuleAnalyzer:
    MAX_MODULES = 13

    def _normalize_name(self, name: str) -> str:
        """Нормализация имени модуля к формату snake_case."""
        name = name.replace(".py", "")
        name = name.strip()
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        name = re.sub(r'([A-Z]+)', lambda m: "_" + m.group(1).lower(), name).lstrip("_")
        return name.lower()

    def _raw_llm(self, prompt: str) -> str:
        """Получение сырого ответа от LLM по переданному промпту."""
        payload = {
            "model": config.MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": config.MAX_TOKENS}
        }
        response = requests.post(config.OLLAMA_URL, json=payload, timeout=config.TIMEOUT)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        return ""

    def _extract_json(self, raw: str) -> str:
        """Извлечение JSON-строки из текста ответа модели."""
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw)
        match = re.search(r'\{[^{}]*\{.*\}[^{}]*\}', raw, re.DOTALL)
        if not match:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError(f"LLM не вернула JSON:\n{raw}")
        return match.group(0)

    def _normalize_manifest(self, data: dict) -> dict:
        """Приведение структуры манифеста к стандартизированному виду."""
        if "project_structure" in data:
            modules = []
            for filename, info in data["project_structure"].items():
                modules.append({
                    "name": self._normalize_name(filename),
                    "description": info.get("description", ""),
                    "depends_on": info.get("depends_on", [])
                })
            data = {"architecture": "MVP", "modules": modules}

        if "modules" not in data:
            raise ValueError("JSON не содержит modules")

        unique = {}
        for m in data["modules"]:
            norm = self._normalize_name(m["name"])
            m["name"] = norm
            if norm not in unique:
                unique[norm] = m

        data["modules"] = list(unique.values())

        if not any(m["name"] == "main" for m in data["modules"]):
            data["modules"].insert(0, {"name": "main", "description": "точка входа", "depends_on": []})

        data["modules"] = data["modules"][:self.MAX_MODULES]
        return data

    def analyze(self, tech_task: str):
        """Анализ технического задания и декомпозиция на модули в формате манифеста."""
        prompt = f"""
            Ты — ИИ-архитектор. Разбей техническое задание на модули Python.

            ПРАВИЛА:
            - Каждый модуль — отдельный .py файл.
            - Имя модуля в snake_case (например, product, bank_account).
            - main — всегда есть, генерируется позже.
            - depends_on — список модулей, от которых зависит текущий (только те, что перечислены в ТЗ).
            - Не создавай модули, которых нет в ТЗ (например, если ТЗ просит класс BankAccount, не создавай модули data, logic).
            - Верни ТОЛЬКО JSON.

            СТРУКТУРА ОТВЕТА:
            {{
            "architecture": "MVP",
            "modules": [
                {{
                "name": "main",
                "description": "главный модуль, точка входа",
                "depends_on": ["product"]
                }},
                {{
                "name": "product",
                "description": "класс Product",
                "depends_on": []
                }}
            ]
            }}

            Техническое задание:
            {tech_task}

            Верни ТОЛЬКО JSON.
            """
        raw = self._raw_llm(prompt)
        if not raw:
            raise ValueError("LLM вернула пустой ответ")
        json_text = self._extract_json(raw)
        data = json.loads(json_text)
        return self._normalize_manifest(data)
