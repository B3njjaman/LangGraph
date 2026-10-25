from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from langgraph.graph import START, StateGraph, MessagesState
from langgraph.prebuilt import tools_condition, ToolNode

def sumar(a: int, b: int) -> int:
    """Suma a y b.

    Args:
        a: primer entero
        b: segundo entero
    """
    return a + b

def multiplicar(a: int, b: int) -> int:
    """Multiplica a y b.

    Args:
        a: primer entero
        b: segundo entero
    """
    return a * b

def dividir(a: int, b: int) -> float:
    """Divide a y b.

    Args:
        a: primer entero
        b: segundo entero
    """
    return a / b

herramientas = [sumar, multiplicar, dividir]

# Definir el LLM con las herramientas enlazadas
llm = ChatOpenAI(model="gpt-4o")
llm_con_herramientas = llm.bind_tools(herramientas)

# Mensaje de sistema
mensaje_sistema = SystemMessage(content="Eres un asistente útil encargado de hacer operaciones aritméticas con un conjunto de entradas.")

# Nodo
def asistente(estado: MessagesState):
   return {"messages": [llm_con_herramientas.invoke([mensaje_sistema] + estado["messages"])]}

# Construir el grafo
constructor = StateGraph(MessagesState)
constructor.add_node("asistente", asistente)
constructor.add_node("tools", ToolNode(herramientas))
constructor.add_edge(START, "asistente")
constructor.add_conditional_edges(
    "asistente",
    # Si el último mensaje (resultado) del asistente es una llamada a herramienta -> tools_condition dirige a tools
    # Si el último mensaje (resultado) del asistente no es una llamada a herramienta -> tools_condition dirige a END
    tools_condition,
)
constructor.add_edge("tools", "asistente")

# Compilar el grafo
grafo = constructor.compile()
