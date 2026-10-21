"""Pruebas de la API (api/app.py). La de /chat real llama al modelo: requiere GOOGLE_API_KEY en .env."""
import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from api.app import app  # noqa: E402


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:  # el "with" ejecuta el arranque (compila el grafo una vez)
        yield c


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "modelo": os.environ.get("MODELO", "gemini-3.5-flash-lite")}


def test_chat_sin_texto_da_422(cliente):
    assert cliente.post("/chat", json={"user_id": "u1"}).status_code == 422


def test_chat_texto_vacio_da_422(cliente):
    assert cliente.post("/chat", json={"user_id": "u1", "texto": ""}).status_code == 422


def test_telegram_acepta_cualquier_json(cliente):
    r = cliente.post("/telegram", json={"update_id": 1, "message": {"text": "hola"}})
    assert r.json() == {"ok": True}


def test_telegram_no_aparece_en_swagger(cliente):
    assert "/telegram" not in cliente.get("/openapi.json").json()["paths"]


def test_si_el_modelo_falla_da_502_sin_detalles(cliente, monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError("GOOGLE_API_KEY=secreta stack interno")

    monkeypatch.setattr(app.state.grafo, "invoke", falla)
    r = cliente.post("/chat", json={"user_id": "u1", "texto": "hola"})
    assert r.status_code == 502
    assert "secreta" not in r.text and "Traceback" not in r.text


@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="falta GOOGLE_API_KEY en .env")
def test_chat_real_preventa(cliente):
    r = cliente.post("/chat", json={"user_id": "test-api", "texto": "¿tienen la polera azul en talla M?"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["ruta"] == "preventa" and cuerpo["motivo"] and cuerpo["respuesta"]
