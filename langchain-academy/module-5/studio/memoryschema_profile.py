from pydantic import BaseModel, Field

from trustcall import create_extractor

from langchain_core.messages import SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore
import configuration

# Inicializamos el LLM
modelo = ChatOpenAI(model="gpt-4o", temperature=0)

# Esquema
class PerfilUsuario(BaseModel):
    """ Perfil de un usuario """
    nombre_usuario: str = Field(description="El nombre preferido del usuario")
    ubicacion_usuario: str = Field(description="La ubicación del usuario")
    intereses: list = Field(description="Una lista con los intereses del usuario")

# Creamos el extractor
extractor_trustcall = create_extractor(
    modelo,
    tools=[PerfilUsuario],
    tool_choice="PerfilUsuario", # Obliga a usar la herramienta PerfilUsuario
)

# Instrucción del chatbot
MENSAJE_SISTEMA_MODELO = """Eres un asistente útil con memoria que entrega información sobre el usuario.
Si tienes memoria de este usuario, úsala para personalizar tus respuestas.
Esta es la memoria (puede estar vacía): {memoria}"""

# Instrucción de extracción
INSTRUCCION_TRUSTCALL = """Crea o actualiza la memoria (documento JSON) para incorporar la información de la siguiente conversación:"""

def llamar_modelo(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Carga la memoria desde el Store y la usa para personalizar la respuesta del chatbot."""

    # Obtenemos la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)

    # Obtenemos el id del usuario desde la configuración
    id_usuario = configurable.id_usuario

    # Recuperamos la memoria desde el Store
    namespace = ("memoria", id_usuario)
    memoria_existente = store.get(namespace, "memoria_usuario")

    # Damos formato a las memorias para el mensaje de sistema
    if memoria_existente and memoria_existente.value:
        dict_memoria = memoria_existente.value
        memoria_formateada = (
            f"Nombre: {dict_memoria.get('nombre_usuario', 'Desconocido')}\n"
            f"Ubicación: {dict_memoria.get('ubicacion_usuario', 'Desconocida')}\n"
            f"Intereses: {', '.join(dict_memoria.get('intereses', []))}"
        )
    else:
        memoria_formateada = None

    # Damos formato a la memoria dentro del mensaje de sistema
    mensaje_sistema = MENSAJE_SISTEMA_MODELO.format(memoria=memoria_formateada)

    # Respondemos usando la memoria y el historial del chat
    respuesta = modelo.invoke([SystemMessage(content=mensaje_sistema)]+estado["messages"])

    return {"messages": respuesta}

def escribir_memoria(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflexiona sobre el historial del chat y guarda una memoria en el Store."""

    # Obtenemos la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)

    # Obtenemos el id del usuario desde la configuración
    id_usuario = configurable.id_usuario

    # Recuperamos la memoria existente desde el Store
    namespace = ("memoria", id_usuario)
    memoria_existente = store.get(namespace, "memoria_usuario")

    # Tomamos el perfil como el valor de la lista y lo convertimos en un documento JSON
    perfil_existente = {"PerfilUsuario": memoria_existente.value} if memoria_existente else None

    # Invocamos el extractor
    resultado = extractor_trustcall.invoke({"messages": [SystemMessage(content=INSTRUCCION_TRUSTCALL)]+estado["messages"], "existing": perfil_existente})

    # Obtenemos el perfil actualizado como un objeto JSON
    perfil_actualizado = resultado["responses"][0].model_dump()

    # Guardamos el perfil actualizado
    clave = "memoria_usuario"
    store.put(namespace, clave, perfil_actualizado)

# Definimos el grafo
constructor = StateGraph(MessagesState,config_schema=configuration.Configuracion)
constructor.add_node("llamar_modelo", llamar_modelo)
constructor.add_node("escribir_memoria", escribir_memoria)
constructor.add_edge(START, "llamar_modelo")
constructor.add_edge("llamar_modelo", "escribir_memoria")
constructor.add_edge("escribir_memoria", END)
grafo = constructor.compile()