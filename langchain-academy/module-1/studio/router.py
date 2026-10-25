from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

# Herramienta
def multiplicar(a: int, b: int) -> int:
    """Multiplica a y b.

    Args:
        a: primer entero
        b: segundo entero
    """
    return a * b

# LLM con la herramienta enlazada
llm = ChatOpenAI(model="gpt-4o")
llm_con_herramientas = llm.bind_tools([multiplicar])

# Nodo
def llamar_llm(estado: MessagesState):
    return {"messages": [llm_con_herramientas.invoke(estado["messages"])]}

# Construir el grafo
constructor = StateGraph(MessagesState)
constructor.add_node("llamar_llm", llamar_llm)
constructor.add_node("tools", ToolNode([multiplicar]))
constructor.add_edge(START, "llamar_llm")
constructor.add_conditional_edges(
    "llamar_llm",
    # Si el último mensaje (resultado) del asistente es una llamada a herramienta -> tools_condition dirige a tools
    # Si el último mensaje (resultado) del asistente no es una llamada a herramienta -> tools_condition dirige a END
    tools_condition,
)
constructor.add_edge("tools", END)

# Compilar el grafo
grafo = constructor.compile()