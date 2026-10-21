"""Pruebas del agente router con los casos de tests/casos_router.json.

El modelo no es determinista: cada caso se ejecuta como test parametrizado (un fallo se marca
como xfail para que se vea sin romper la suite) y test_minimo_aciertos exige al menos 13 de 15.
Requieren GOOGLE_API_KEY en .env.
"""
import json
import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

from src.router.graph import graph  # noqa: E402

CASOS = json.loads((Path(__file__).parent / "casos_router.json").read_text(encoding="utf-8"))
MINIMO_ACIERTOS = 13
RESULTADOS: dict[str, str] = {}  # mensaje -> ruta obtenida

requiere_clave = pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="falta GOOGLE_API_KEY en .env")


def enrutar(mensaje: str) -> str:
    if mensaje not in RESULTADOS:
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        RESULTADOS[mensaje] = graph.invoke({"mensaje": mensaje}, config)["ruta"]
    return RESULTADOS[mensaje]


def test_hay_15_casos_balanceados():
    assert len(CASOS) == 15
    for ruta in ("preventa", "postventa", "generica"):
        assert sum(c["esperado"] == ruta for c in CASOS) == 5


def test_diagrama_tiene_los_cuatro_nodos():
    mermaid = graph.get_graph().draw_mermaid()
    for nodo in ("router", "agente_preventa", "agente_postventa", "respuesta_generica"):
        assert nodo in mermaid


@requiere_clave
@pytest.mark.parametrize("caso", CASOS, ids=[c["mensaje"] for c in CASOS])
def test_caso(caso):
    obtenido = enrutar(caso["mensaje"])
    if obtenido != caso["esperado"]:
        pytest.xfail(f"esperado {caso['esperado']}, obtuvo {obtenido}")


@requiere_clave
def test_minimo_aciertos():
    aciertos = sum(enrutar(c["mensaje"]) == c["esperado"] for c in CASOS)
    assert aciertos >= MINIMO_ACIERTOS, f"solo {aciertos}/{len(CASOS)} aciertos (mínimo {MINIMO_ACIERTOS})"
