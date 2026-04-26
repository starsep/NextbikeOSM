run:
    uv run main.py
test:
    uv run pytest
ruff:
    uv run ruff format .
    uv run ruff check --fix .
