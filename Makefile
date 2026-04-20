.PHONY: install api ui demo eval test ci docker-build docker-up docker-down

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -e .

api:
	./scripts/run_api.sh

ui:
	./scripts/run_ui.sh

demo:
	. .venv/bin/activate && python scripts/run_demo.py

eval:
	. .venv/bin/activate && python evals/runner.py

test:
	. .venv/bin/activate && python -m pytest -q

ci:
	. .venv/bin/activate && python -m pytest -q

docker-build:
	docker build -t multi-agent-app-scaffolder:latest .

docker-up:
	docker compose up --build

docker-down:
	docker compose down
