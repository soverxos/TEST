# Makefile для SwiftDevBot

.PHONY: help install dev test lint format type-check docker-build docker-up docker-down clean

help: ## Показать справку
	@echo "SwiftDevBot - Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt

dev: ## Установить зависимости для разработки
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio pylint black isort mypy

test: ## Запустить тесты
	pytest tests/ -v

web-test: ## Запустить web API тесты через .venv
	. .venv/bin/activate && pytest tests/test_web_app.py

test-cov: ## Запустить тесты с покрытием
	pytest tests/ --cov=Systems/core --cov-report=html --cov-report=term

lint: ## Проверить код линтером
	pylint Systems/core --disable=all --enable=E,F,W

format: ## Форматировать код
	black Systems/
	isort Systems/

format-check: ## Проверить форматирование кода
	black --check Systems/
	isort --check Systems/

type-check: ## Проверить типы
	mypy Systems/core --ignore-missing-imports

docker-build: ## Собрать Docker образ
	docker build -t swiftdevbot:latest .

docker-up: ## Запустить Docker Compose
	docker-compose up -d

docker-down: ## Остановить Docker Compose
	docker-compose down

docker-logs: ## Показать логи Docker
	docker-compose logs -f

clean: ## Очистить временные файлы
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

setup: ## Первоначальная настройка проекта
	python3 sdb_setup.py

run: ## Запустить бота
	python3 sdb.py run

run-verbose: ## Запустить бота с подробными логами
	python3 sdb.py run -v

run-debug: ## Запустить бота в режиме отладки
	python3 sdb.py run -d

status: ## Показать статус бота
	python3 sdb.py status

stop: ## Остановить бота
	python3 sdb.py stop

restart: ## Перезапустить бота
	python3 sdb.py restart

db-init: ## Инициализировать базу данных
	python3 sdb.py db init

db-migrate: ## Применить миграции
	python3 sdb.py db migrate

db-upgrade: ## Обновить схему БД
	python3 sdb.py db upgrade

all: format lint type-check test ## Запустить все проверки

