"""Agente router del chat de un ecommerce: decide si el mensaje va a preventa, postventa o genérica.

Flujo:  START → router ─┬→ agente_preventa    → END   (Gemini, prompt de vendedor)
                        ├→ agente_postventa   → END   (Gemini, prompt de soporte)
                        └→ respuesta_generica → END
"""
import os
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from src.router.prompts import PROMPT_POSTVENTA, PROMPT_PREVENTA, PROMPT_ROUTER, RESPUESTA_GENERICA

load_dotenv()


class Estado(TypedDict, total=False):
    mensaje: str
    ruta: str
    motivo: str
    respuesta: str
    messages: Annotated[list, add_messages]  # memoria por thread_id (MemorySaver)


class Decision(BaseModel):
    ruta: Literal["preventa", "postventa", "generica"] = Field(description="A qué agente va el mensaje.")
    motivo: str = Field(description="Una frase: por qué esa ruta.")


llm = ChatGoogleGenerativeAI(model=os.environ.get("MODELO", "gemini-3.5-flash-lite"), temperature=0)
llm_router = llm.with_structured_output(Decision)


def router(estado: Estado) -> dict:
    historial = estado.get("messages", [])
    decision = llm_router.invoke(
        [SystemMessage(PROMPT_ROUTER), *historial, HumanMessage(estado["mensaje"])]
    )
    return {
        "ruta": decision.ruta,
        "motivo": decision.motivo,
        "messages": [HumanMessage(estado["mensaje"])],
    }


def responder_con(prompt: str, estado: Estado) -> dict:
    # "messages" ya trae el historial del hilo más el mensaje actual (lo agregó el router).
    respuesta = llm.invoke([SystemMessage(prompt), *estado["messages"]]).text
    return {"respuesta": respuesta, "messages": [AIMessage(respuesta)]}


def agente_preventa(estado: Estado) -> dict:
    return responder_con(PROMPT_PREVENTA, estado)


def agente_postventa(estado: Estado) -> dict:
    return responder_con(PROMPT_POSTVENTA, estado)


def respuesta_generica(estado: Estado) -> dict:
    return {"respuesta": RESPUESTA_GENERICA, "messages": [AIMessage(RESPUESTA_GENERICA)]}


def elegir_destino(estado: Estado) -> str:
    return estado["ruta"]


constructor = StateGraph(Estado)
constructor.add_node("router", router)
constructor.add_node("agente_preventa", agente_preventa)
constructor.add_node("agente_postventa", agente_postventa)
constructor.add_node("respuesta_generica", respuesta_generica)

constructor.add_edge(START, "router")
constructor.add_conditional_edges(
    "router",
    elegir_destino,
    {"preventa": "agente_preventa", "postventa": "agente_postventa", "generica": "respuesta_generica"},
)
constructor.add_edge("agente_preventa", END)
constructor.add_edge("agente_postventa", END)
constructor.add_edge("respuesta_generica", END)

graph = constructor.compile(checkpointer=MemorySaver())
