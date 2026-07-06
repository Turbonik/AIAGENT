"""Обработчики PDF, DOCX и TXT файлов для извлечения текста."""

import re
from pathlib import Path
from typing import Optional
import sys
 
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return get_base_dir()

def extract_text_from_txt(file_path: str) -> Optional[str]:
    """Извлекает текст из TXT файла."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        return f"Ошибка чтения TXT: {str(e)}"


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """Извлекает текст из PDF файла."""
    try:
        import PyPDF2
        
        text = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text())
        return '\n'.join(text).strip()
    except ImportError:
        return "Ошибка: установите PyPDF2 (pip install PyPDF2)"
    except Exception as e:
        return f"Ошибка чтения PDF: {str(e)}"


def extract_text_from_docx(file_path: str) -> Optional[str]:
    """Извлекает текст из DOCX файла."""
    try:
        from docx import Document
        
        doc = Document(file_path)
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)
        return '\n'.join(text).strip()
    except ImportError:
        return "Ошибка: установите python-docx (pip install python-docx)"
    except Exception as e:
        return f"Ошибка чтения DOCX: {str(e)}"


def extract_text_from_file(file_path: str) -> Optional[str]:
    """Определяет тип файла и извлекает текст."""
    file_path = str(file_path)
    ext = Path(file_path).suffix.lower()
    
    if ext == '.txt':
        return extract_text_from_txt(file_path)
    elif ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    else:
        return f"Ошибка: неподдерживаемый формат {ext}"


def merge_texts(*texts: str) -> str:
    """Объединяет несколько текстов в один, удаляя пустые строки."""
    merged = []
    for text in texts:
        if text and isinstance(text, str):
            text = text.strip()
            if text:
                merged.append(text)
    return '\n\n'.join(merged)


def validate_file(file_path: str) -> tuple[bool, str]:
    """Проверяет, является ли файл поддерживаемым форматом."""
    ext = Path(file_path).suffix.lower()
    if ext not in ['.txt', '.pdf', '.docx']:
        return False, f"Поддерживаются только .txt, .pdf, .docx. Получен: {ext}"
    
    if not Path(file_path).exists():
        return False, "Файл не найден"
    
    return True, ""
