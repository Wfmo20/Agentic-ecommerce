"""Corre el router con los casos de tests/casos_router.json y muestra una tabla de resultados.

Uso (desde la raíz del proyecto):  python scripts/test_router.py
"""
import json
import sys
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # para poder importar src/ desde scripts/
sys.stdout.reconfigure(encoding="utf-8")

from src.router.graph import graph  # noqa: E402

casos = json.loads((RAIZ / "tests" / "casos_router.json").read_text(encoding="utf-8"))


def recortar(texto: str, largo: int) -> str:
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"


print(f"{'MENSAJE':<45} {'ESPERADO':<10} {'OBTENIDO':<10} OK  MOTIVO")
print("-" * 130)

fallados = []
for caso in casos:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}  # cada caso en su propia conversación
    estado = graph.invoke({"mensaje": caso["mensaje"]}, config)
    acierto = estado["ruta"] == caso["esperado"]
    if not acierto:
        fallados.append((caso, estado))
    print(
        f"{recortar(caso['mensaje'], 45):<45} {caso['esperado']:<10} {estado['ruta']:<10} "
        f"{'✔' if acierto else '✘'}   {estado['motivo']}"
    )

aciertos = len(casos) - len(fallados)
print("-" * 130)
print(f"Aciertos: {aciertos}/{len(casos)} ({aciertos / len(casos):.0%})")

if fallados:
    print("\nFallados:")
    for caso, estado in fallados:
        print(f"  ✘ \"{caso['mensaje']}\" → esperado {caso['esperado']}, obtuvo {estado['ruta']}")
        print(f"    Motivo: {estado['motivo']}")
