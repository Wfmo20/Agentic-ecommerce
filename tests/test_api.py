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


SECRETO = "secreto-de-prueba"
UPDATE = {"update_id": 1, "message": {"chat": {"id": 42}, "text": "¿tienen la polera azul en talla M?"}}


@pytest.fixture
def telegram_falso(monkeypatch):
    """Fija el secreto, reemplaza el grafo y guarda lo que se le "enviaría" a Telegram (sin llamarlo)."""
    monkeypatch.setenv("TELEGRAM_SECRET", SECRETO)
    enviados = []
    monkeypatch.setattr("api.app.enviar_a_telegram", lambda chat_id, texto: enviados.append((chat_id, texto)))
    monkeypatch.setattr(app.state.grafo, "invoke", lambda entrada, config: {"respuesta": f"eco: {entrada['mensaje']}"})
    return enviados


def test_telegram_sin_secreto_da_403(cliente, telegram_falso):
    r = cliente.post("/telegram", json=UPDATE)
    assert r.status_code == 403
    assert telegram_falso == []


def test_telegram_secreto_incorrecto_da_403(cliente, telegram_falso):
    r = cliente.post("/telegram", json=UPDATE, headers={"X-Telegram-Bot-Api-Secret-Token": "otro"})
    assert r.status_code == 403


def test_telegram_responde_al_chat(cliente, telegram_falso):
    r = cliente.post("/telegram", json=UPDATE, headers={"X-Telegram-Bot-Api-Secret-Token": SECRETO})
    assert r.json() == {"ok": True}
    assert telegram_falso == [(42, "eco: ¿tienen la polera azul en talla M?")]


def test_telegram_ignora_mensajes_sin_texto(cliente, telegram_falso):
    sticker = {"update_id": 2, "message": {"chat": {"id": 42}, "sticker": {}}}
    r = cliente.post("/telegram", json=sticker, headers={"X-Telegram-Bot-Api-Secret-Token": SECRETO})
    assert r.json() == {"ok": True}
    assert telegram_falso == []


def test_telegram_si_el_modelo_falla_avisa_al_usuario(cliente, telegram_falso, monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError("GOOGLE_API_KEY=secreta")

    monkeypatch.setattr(app.state.grafo, "invoke", falla)
    r = cliente.post("/telegram", json=UPDATE, headers={"X-Telegram-Bot-Api-Secret-Token": SECRETO})
    assert r.status_code == 200
    assert telegram_falso[0][0] == 42 and "secreta" not in telegram_falso[0][1]


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
