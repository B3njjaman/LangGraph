import random
from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

# Estado
class Estado(TypedDict):
    estado_grafo: str

# Arista condicional
def decidir_animo(estado) -> Literal["nodo_2", "nodo_3"]:

    # Muchas veces usaremos el estado para decidir cuál es el siguiente nodo
    entrada_usuario = estado['estado_grafo']

    # Aquí hacemos un reparto 50 / 50 entre los nodos 2 y 3
    if random.random() < 0.5:

        # El 50% de las veces devolvemos el nodo 2
        return "nodo_2"

    # El 50% de las veces devolvemos el nodo 3
    return "nodo_3"

# Nodos
def nodo_1(estado):
    print("---Nodo 1---")
    return {"estado_grafo":estado['estado_grafo'] +" Me siento"}

def nodo_2(estado):
    print("---Nodo 2---")
    return {"estado_grafo":estado['estado_grafo'] +" feliz."}

def nodo_3(estado):
    print("---Nodo 3---")
    return {"estado_grafo":estado['estado_grafo'] +" triste."}

# Construir el grafo
constructor = StateGraph(Estado)
constructor.add_node("nodo_1", nodo_1)
constructor.add_node("nodo_2", nodo_2)
constructor.add_node("nodo_3", nodo_3)
constructor.add_edge(START, "nodo_1")
constructor.add_conditional_edges("nodo_1", decidir_animo)
constructor.add_edge("nodo_2", END)
constructor.add_edge("nodo_3", END)

# Compilar el grafo
grafo = constructor.compile()