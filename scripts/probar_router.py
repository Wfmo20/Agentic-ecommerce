"""Prueba el agente router con los 6 mensajes del taller y muestra la ruta de cada uno.

Uso (desde la raíz del proyecto):  python scripts/probar_router.py
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # para poder importar src/ desde scripts/
sys.stdout.reconfigure(encoding="utf-8")

from src.router.graph import graph  # noqa: E402

MENSAJES = [
    "¿tienen la polera azul en talla M?",
    "mi pedido 4521 llegó roto",
    "hola",
    "¿cuánto cuesta el envío a Valparaíso?",
    "quiero devolver unas zapatillas",
    "¿qué hora es en Tokio?",
]

for numero, mensaje in enumerate(MENSAJES, start=1):
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}  # cada mensaje en su propia conversación
    saltos = [nodo for paso in graph.stream({"mensaje": mensaje}, config, stream_mode="updates") for nodo in paso]
    estado = graph.get_state(config).values

    print(f"{numero}. \"{mensaje}\"")
    print(f"   Ruta:      {estado['ruta']}")
    print(f"   Saltos:    {' → '.join(saltos)}")
    print(f"   Motivo:    {estado['motivo']}")
    print(f"   Respuesta: {estado['respuesta']}")
    print()
