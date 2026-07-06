"""Основные настройки агента для работы с OLLAMA и Docker."""

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:1.5b"
TEMPERATURE = 0.2
MAX_TOKENS = 50000
TIMEOUT = 60
DOCKER_IMAGE = "python:3.10-slim"
DOCKER_MEMORY_LIMIT = "256m"
DOCKER_TIMEOUT = 30