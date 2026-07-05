import re
import requests
from . import config

def clean_code(raw: str) -> str:
    if not raw:
        return ""
    if raw.startswith('\ufeff'):
        raw = raw[1:]
    match = re.search(r'```(?:python)?\s*\n(.*?)```', raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = raw.splitlines()
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(('def ', 'import ', 'from ', 'class ')):
            start = i
            break
    else:
        return re.sub(r'```', '', raw).strip()
    code_lines = lines[start:]
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()
    cleaned = []
    in_marker = False
    for line in code_lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_marker = not in_marker
            continue
        if not in_marker:
            cleaned.append(line)
    return '\n'.join(cleaned).strip()

def generate_code(prompt: str):
    payload = {
        "model": config.MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": config.TEMPERATURE,
            "num_predict": config.MAX_TOKENS
        }
    }
    try:
        response = requests.post(config.OLLAMA_URL, json=payload, timeout=config.TIMEOUT)
        if response.status_code == 200:
            raw = response.json().get("response", "").strip()
            cleaned = clean_code(raw)
            return cleaned if cleaned else None
        else:
            print(f"Ollama returned {response.status_code}")
            return None
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

class CodeGenerator:
    def generate_code(self, prompt: str):
        return generate_code(prompt)
