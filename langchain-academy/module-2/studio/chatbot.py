from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END

# Usaremos este modelo tanto para la conversación como para el resumen
from langchain_openai import ChatOpenAI
modelo = ChatOpenAI(model="gpt-4o", temperature=0)

# Clase de estado para guardar los mensajes y el resumen
class Estado(MessagesState):
    resumen: str

# Define la lógica para llamar al modelo
def llamar_modelo(estado: Estado):

    # Obtiene el resumen si existe
    resumen = estado.get("resumen", "")

    # Si hay un resumen, lo agregamos a los mensajes
    if resumen:

        # Agrega el resumen al mensaje de sistema
        mensaje_sistema = f"Resumen de la conversación anterior: {resumen}"

        # Agrega el resumen antes de los mensajes más recientes
        mensajes = [SystemMessage(content=mensaje_sistema)] + estado["messages"]

    else:
        mensajes = estado["messages"]

    respuesta = modelo.invoke(mensajes)
    return {"messages": respuesta}

# Decide si terminar o resumir la conversación
def debe_continuar(estado: Estado) -> Literal["resumir_conversacion", "__end__"]:

    """Devuelve el siguiente nodo a ejecutar."""

    mensajes = estado["messages"]

    # Si hay más de seis mensajes, resumimos la conversación
    if len(mensajes) > 6:
        return "resumir_conversacion"

    # Si no, podemos terminar
    return END

def resumir_conversacion(estado: Estado):

    # Primero obtenemos el resumen si existe
    resumen = estado.get("resumen", "")

    # Creamos el prompt para resumir
    if resumen:

        # Si ya existe un resumen, lo agregamos al prompt
        mensaje_resumen = (
            f"Este es el resumen de la conversación hasta ahora: {resumen}\n\n"
            "Amplía el resumen teniendo en cuenta los nuevos mensajes de arriba:"
        )

    else:
        # Si no existe un resumen, creamos uno nuevo
        mensaje_resumen = "Crea un resumen de la conversación de arriba:"

    # Agrega el prompt a nuestro historial
    mensajes = estado["messages"] + [HumanMessage(content=mensaje_resumen)]
    respuesta = modelo.invoke(mensajes)

    # Borra todos los mensajes menos los 2 más recientes y agrega el resumen al estado
    mensajes_a_borrar = [RemoveMessage(id=m.id) for m in estado["messages"][:-2]]
    return {"resumen": respuesta.content, "messages": mensajes_a_borrar}

# Define un nuevo grafo
flujo = StateGraph(Estado)
flujo.add_node("conversacion", llamar_modelo)
flujo.add_node(resumir_conversacion)

# Define la conversación como punto de entrada
flujo.add_edge(START, "conversacion")
flujo.add_conditional_edges("conversacion", debe_continuar)
flujo.add_edge("resumir_conversacion", END)

# Compila
grafo = flujo.compile()
