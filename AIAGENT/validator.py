import ast

def validate_syntax(code: str):
    """Validates Python syntax using compile."""
    if not code or not code.strip():
        return False, "Empty code"
    try:
        compile(code, '<string>', 'exec')
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error: {e}"