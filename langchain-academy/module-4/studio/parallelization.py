import operator
from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from langchain_community.document_loaders import WikipediaLoader
from langchain_tavily import TavilySearch  # actualizado 1.0

from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class Estado(TypedDict):
    pregunta: str
    respuesta: str
    contexto: Annotated[list, operator.add]

def buscar_web(estado):

    """ Recupera documentos con una búsqueda web """

    # Búsqueda
    busqueda_tavily = TavilySearch(max_results=3)
    datos = busqueda_tavily.invoke({"query": estado['pregunta']})
    docs_busqueda = datos.get("results", datos)

     # Formato
    docs_busqueda_formateados = "\n\n---\n\n".join(
        [
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in docs_busqueda
        ]
    )

    return {"contexto": [docs_busqueda_formateados]}

def buscar_wikipedia(estado):

    """ Recupera documentos de Wikipedia """

    # Búsqueda
    docs_busqueda = WikipediaLoader(query=estado['pregunta'],
                                  load_max_docs=2).load()

     # Formato
    docs_busqueda_formateados = "\n\n---\n\n".join(
        [
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content}\n</Document>'
            for doc in docs_busqueda
        ]
    )

    return {"contexto": [docs_busqueda_formateados]}

def generar_respuesta(estado):

    """ Nodo para responder una pregunta """

    # Obtenemos el estado
    contexto = estado["contexto"]
    pregunta = estado["pregunta"]

    # Plantilla
    plantilla_respuesta = """Responde la pregunta {pregunta} usando este contexto: {contexto}"""
    instrucciones_respuesta = plantilla_respuesta.format(pregunta=pregunta,
                                                       contexto=contexto)

    # Respuesta
    respuesta = llm.invoke([SystemMessage(content=instrucciones_respuesta)]+[HumanMessage(content=f"Responde la pregunta.")])

    # La agregamos al estado
    return {"respuesta": respuesta}

# Agregamos los nodos
constructor = StateGraph(Estado)

# Inicializamos cada nodo
constructor.add_node("buscar_web",buscar_web)
constructor.add_node("buscar_wikipedia", buscar_wikipedia)
constructor.add_node("generar_respuesta", generar_respuesta)

# Flujo
constructor.add_edge(START, "buscar_wikipedia")
constructor.add_edge(START, "buscar_web")
constructor.add_edge("buscar_wikipedia", "generar_respuesta")
constructor.add_edge("buscar_web", "generar_respuesta")
constructor.add_edge("generar_respuesta", END)
grafo = constructor.compile()
