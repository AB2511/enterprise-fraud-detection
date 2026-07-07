.PHONY: help install dev test lint format clean docker-build docker-up docker-down migrate

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make dev          - Install development dependencies"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run all linters"
	@echo "  make format       - Format code with black and isort"
	@echo "  make clean        - Clean cache and build files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start services with docker-compose"
	@echo "  make docker-down  - Stop services"
	@echo "  make migrate      - Run database migrations"
	@echo "  make run          - Run development server"

install:
	poetry install --no-dev

dev:
	poetry install

test:
	poetry run pytest --cov=src --cov-report=term --cov-report=html

lint:
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check-only .
	poetry run mypy src/

format:
	poetry run black .
	poetry run isort .
	poetry run ruff check --fix .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

docker-build:
	docker build -t fraud-detection-api:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

migrate:
	poetry run alembic upgrade head

run:
	poetry run uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000
