import operator
from typing import Annotated
from typing_extensions import TypedDict

from pydantic import BaseModel

from langchain_openai import ChatOpenAI

from langgraph.constants import Send
from langgraph.graph import END, StateGraph, START

# Prompts que vamos a usar
prompt_subtemas = """Genera una lista de 3 subtemas, todos relacionados con este tema general: {tema}."""
prompt_chiste = """Genera un chiste sobre {subtema}"""
prompt_mejor_chiste = """A continuación hay varios chistes sobre {tema}. ¡Elige el mejor! Devuelve el ID del mejor, usando 0 como ID del primer chiste. Chistes: \n\n  {chistes}"""

# LLM
modelo = ChatOpenAI(model="gpt-4o", temperature=0)

# Definimos el estado
class Subtemas(BaseModel):
    subtemas: list[str]

class MejorChiste(BaseModel):
    id: int

class EstadoGeneral(TypedDict):
    tema: str
    subtemas: list
    chistes: Annotated[list, operator.add]
    mejor_chiste_elegido: str

def generar_temas(estado: EstadoGeneral):
    prompt = prompt_subtemas.format(tema=estado["tema"])
    respuesta = modelo.with_structured_output(Subtemas).invoke(prompt)
    return {"subtemas": respuesta.subtemas}

class EstadoChiste(TypedDict):
    subtema: str

class Chiste(BaseModel):
    chiste: str

def generar_chiste(estado: EstadoChiste):
    prompt = prompt_chiste.format(subtema=estado["subtema"])
    respuesta = modelo.with_structured_output(Chiste).invoke(prompt)
    return {"chistes": [respuesta.chiste]}

def mejor_chiste(estado: EstadoGeneral):
    chistes = "\n\n".join(estado["chistes"])
    prompt = prompt_mejor_chiste.format(tema=estado["tema"], chistes=chistes)
    respuesta = modelo.with_structured_output(MejorChiste).invoke(prompt)
    return {"mejor_chiste_elegido": estado["chistes"][respuesta.id]}

def ir_a_chistes(estado: EstadoGeneral):
    return [Send("generar_chiste", {"subtema": s}) for s in estado["subtemas"]]

# Construimos el grafo: aquí juntamos todo
constructor_grafo = StateGraph(EstadoGeneral)
constructor_grafo.add_node("generar_temas", generar_temas)
constructor_grafo.add_node("generar_chiste", generar_chiste)
constructor_grafo.add_node("mejor_chiste", mejor_chiste)
constructor_grafo.add_edge(START, "generar_temas")
constructor_grafo.add_conditional_edges("generar_temas", ir_a_chistes, ["generar_chiste"])
constructor_grafo.add_edge("generar_chiste", "mejor_chiste")
constructor_grafo.add_edge("mejor_chiste", END)

# Compilamos el grafo
grafo = constructor_grafo.compile()
