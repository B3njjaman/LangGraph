import uuid

from pydantic import BaseModel, Field

from trustcall import create_extractor

from langchain_core.messages import SystemMessage
from langchain_core.messages import merge_message_runs
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore
import configuration

# Inicializamos el LLM
modelo = ChatOpenAI(model="gpt-4o", temperature=0)

# Esquema de memoria
class Memoria(BaseModel):
    contenido: str = Field(description="El contenido principal de la memoria. Por ejemplo: El usuario expresó interés en aprender francés.")

# Creamos el extractor de Trustcall
extractor_trustcall = create_extractor(
    modelo,
    tools=[Memoria],
    tool_choice="Memoria",
    # Esto permite que el extractor inserte memorias nuevas
    enable_inserts=True,
)

# Instrucción del chatbot
MENSAJE_SISTEMA_MODELO = """Eres un chatbot útil. Estás diseñado para ser un compañero del usuario.

Tienes una memoria a largo plazo que lleva el registro de la información que aprendes sobre el usuario con el tiempo.

Memoria actual (puede incluir memorias actualizadas durante esta conversación):

{memoria}"""

# Instrucción de Trustcall
INSTRUCCION_TRUSTCALL = """Reflexiona sobre la siguiente interacción.

Usa las herramientas disponibles para conservar las memorias necesarias sobre el usuario.

Usa llamadas a herramientas en paralelo para manejar las actualizaciones y las inserciones al mismo tiempo:"""
def llamar_modelo(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Carga las memorias desde el Store y las usa para personalizar la respuesta del chatbot."""

    # Obtenemos la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)

    # Obtenemos el id del usuario desde la configuración
    id_usuario = configurable.id_usuario

    # Recuperamos la memoria desde el Store
    namespace = ("memorias", id_usuario)
    memorias = store.search(namespace)

    # Damos formato a las memorias para el mensaje de sistema
    informacion = "\n".join(f"- {mem.value['contenido']}" for mem in memorias)
    mensaje_sistema = MENSAJE_SISTEMA_MODELO.format(memoria=informacion)

    # Respondemos usando la memoria y el historial del chat
    respuesta = modelo.invoke([SystemMessage(content=mensaje_sistema)]+estado["messages"])

    return {"messages": respuesta}

def escribir_memoria(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflexiona sobre el historial del chat y guarda una memoria en el Store."""

    # Obtenemos la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)

    # Obtenemos el id del usuario desde la configuración
    id_usuario = configurable.id_usuario

    # Definimos el namespace de las memorias
    namespace = ("memorias", id_usuario)

    # Recuperamos las memorias más recientes como contexto
    elementos_existentes = store.search(namespace)

    # Damos formato a las memorias existentes para el extractor de Trustcall
    nombre_herramienta = "Memoria"
    memorias_existentes = ([(elemento_existente.key, nombre_herramienta, elemento_existente.value)
                            for elemento_existente in elementos_existentes]
                            if elementos_existentes
                            else None
                          )

    # Combinamos el historial del chat y la instrucción
    mensajes_actualizados=list(merge_message_runs(messages=[SystemMessage(content=INSTRUCCION_TRUSTCALL)] + estado["messages"]))

    # Invocamos el extractor
    resultado = extractor_trustcall.invoke({"messages": mensajes_actualizados,
                                            "existing": memorias_existentes})

    # Guardamos en el Store las memorias de Trustcall
    for r, meta_r in zip(resultado["responses"], resultado["response_metadata"]):
        store.put(namespace,
                  meta_r.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )

# Definimos el grafo
constructor = StateGraph(MessagesState,config_schema=configuration.Configuracion)
constructor.add_node("llamar_modelo", llamar_modelo)
constructor.add_node("escribir_memoria", escribir_memoria)
constructor.add_edge(START, "llamar_modelo")
constructor.add_edge("llamar_modelo", "escribir_memoria")
constructor.add_edge("escribir_memoria", END)
grafo = constructor.compile()