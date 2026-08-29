.PHONY: install run test smoke docker
install:
	python -m pip install -e '.[dev]'
run:
	python -m polyquant
test:
	pytest -q
smoke:
	python scripts/smoke.py
docker:
	docker compose up --build
