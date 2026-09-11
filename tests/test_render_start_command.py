"""Render start-command contract: gunicorn binds $PORT; bake stays off the web build."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def test_render_start_command_binds_port_unbuffered():
    text = (_ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "PYTHONUNBUFFERED" in text
    assert "python -u -m gunicorn" in text
    assert "--bind 0.0.0.0:$PORT" in text
    assert "backend.main:app" in text


def test_render_web_build_does_not_bake_duckdb():
    text = (_ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "buildCommand: pip install -r requirements.txt\n" in text.replace(
        "\r\n", "\n"
    )
    assert "bake_db.py" not in text.split("buildCommand:", 1)[1].split("\n", 1)[0]
    assert "validate_db_completeness.py" not in text.split("buildCommand:", 1)[1].split(
        "\n", 1
    )[0]


def test_dockerfile_cmd_exec_binds_port_env():
    text = (_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "CMD exec python -u -m gunicorn" in text
    assert "0.0.0.0:${PORT:-8000}" in text
    assert '"0.0.0.0:8000"' not in text
