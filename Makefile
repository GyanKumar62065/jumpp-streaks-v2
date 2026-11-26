.PHONY: up down test seed rebuild csv

up:
	docker compose up --build -d

down:
	docker compose down

test:
	docker compose run --rm api pytest -q

seed:
	docker compose run --rm api python -m streaks.cli seed

rebuild:
	docker compose run --rm api python -m streaks.cli rebuild

csv:
	docker compose run --rm api python -m streaks.cli export-csv --as-of 2026-11-15T10:00:00+05:30 --out streaks_as_of_2026-11-15T1000IST.csv
