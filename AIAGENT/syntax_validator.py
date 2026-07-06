import ast

def validate_syntax(code: str):
    """Проверяет синтаксис Python кода с использованием compile."""
    if not code or not code.strip():
        return False, "Empty code"
    try:
        compile(code, '<string>', 'exec')
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error: {e}"