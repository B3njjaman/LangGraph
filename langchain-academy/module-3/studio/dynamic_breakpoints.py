from typing_extensions import TypedDict
from langgraph.errors import NodeInterrupt
from langgraph.graph import START, END, StateGraph

class Estado(TypedDict):
    entrada: str

def paso_1(estado: Estado) -> Estado:
    print("---Paso 1---")
    return estado

def paso_2(estado: Estado) -> Estado:
    # Lanzamos una NodeInterrupt de forma opcional si la entrada tiene más de 5 caracteres
    if len(estado['entrada']) > 5:
        raise NodeInterrupt(f"Se recibió una entrada de más de 5 caracteres: {estado['entrada']}")

    print("---Paso 2---")
    return estado

def paso_3(estado: Estado) -> Estado:
    print("---Paso 3---")
    return estado

constructor = StateGraph(Estado)
constructor.add_node("paso_1", paso_1)
constructor.add_node("paso_2", paso_2)
constructor.add_node("paso_3", paso_3)
constructor.add_edge(START, "paso_1")
constructor.add_edge("paso_1", "paso_2")
constructor.add_edge("paso_2", "paso_3")
constructor.add_edge("paso_3", END)

grafo = constructor.compile()