# Rag Time Art Facts API

FastAPI scaffold for a backend service that can grow into a model orchestration and art facts API.

## Project structure

```text
.
|-- .vscode/
|   `-- launch.json
|-- app/
|   |-- api/
|   |   |-- __init__.py
|   |   `-- routes.py
|   |-- __init__.py
|   `-- main.py
|-- .gitignore
|-- main.py
`-- pyproject.toml
```

## Requirements

- `uv` installed locally
- Python 3.12+

## Setup

Create the virtual environment and install dependencies with `uv`:

```bash
uv sync
```

This creates `.venv/` automatically and installs FastAPI plus Uvicorn.

## Run with hot reload

From the project root:

```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Docs will be available at `http://127.0.0.1:8000/docs`.

## VS Code debug

Use the `FastAPI: uvicorn (reload)` launch configuration in the Run and Debug panel. It starts Uvicorn with `--reload` in the integrated terminal.

## Current endpoints

- `GET /`
- `GET /health`
