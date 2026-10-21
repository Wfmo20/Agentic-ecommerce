"""Ejecuta un agente desde la raíz del proyecto.

Uso:
    python main.py {nombre_agente} "mensaje"              ejecuta el agente
    python main.py {nombre_agente} "mensaje" --saltos     además muestra los nodos recorridos
    python main.py {nombre_agente} --diagrama             imprime el Mermaid del grafo (no lo ejecuta)
"""
import argparse
import importlib
import sys

sys.stdout.reconfigure(encoding="utf-8")


def cargar_grafo(nombre_agente: str):
    try:
        return importlib.import_module(f"src.{nombre_agente}.graph").graph
    except ModuleNotFoundError:
        sys.exit(f"No existe el agente '{nombre_agente}' (se busca en src/{nombre_agente}/graph.py).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta un agente de src/{nombre_agente}/.")
    parser.add_argument("agente", help="Nombre de la carpeta del agente en src/ (ej.: router)")
    parser.add_argument("mensaje", nargs="?", help="Mensaje para el agente")
    parser.add_argument("--saltos", action="store_true", help="Imprime los nodos por los que pasó el grafo")
    parser.add_argument("--diagrama", action="store_true", help="Imprime el Mermaid del grafo sin ejecutarlo")
    parser.add_argument("--thread", default="consola", help="thread_id de la conversación (memoria)")
    args = parser.parse_args()

    grafo = cargar_grafo(args.agente)

    if args.diagrama:
        print(grafo.get_graph().draw_mermaid())
        return

    if not args.mensaje:
        parser.error('falta el mensaje: python main.py {nombre_agente} "mensaje"')

    config = {"configurable": {"thread_id": args.thread}}
    saltos = []
    for paso in grafo.stream({"mensaje": args.mensaje}, config, stream_mode="updates"):
        saltos.extend(paso.keys())
    estado = grafo.get_state(config).values

    if args.saltos:
        print("Saltos: " + " → ".join(saltos))
        if estado.get("motivo"):
            print(f"Motivo: {estado['motivo']}")
        print()

    for clave in ("ruta", "motivo"):
        if clave in estado and not args.saltos:
            print(f"{clave.capitalize()}: {estado[clave]}")
    print(estado.get("respuesta", estado))


if __name__ == "__main__":
    main()
