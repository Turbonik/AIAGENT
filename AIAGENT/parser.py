import re

def extract_tests(tech_task: str):
    """Extracts lines starting with 'assert' from the technical specification."""
    lines = tech_task.split('\n')
    return [line.strip() for line in lines if line.strip().startswith('assert')]