from langchain_core.messages import SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore
import configuration

# Inicializamos el LLM
modelo = ChatOpenAI(model="gpt-4o", temperature=0)

# Instrucción del chatbot
MENSAJE_SISTEMA_MODELO = """Eres un asistente útil con memoria que entrega información sobre el usuario.
Si tienes memoria de este usuario, úsala para personalizar tus respuestas.
Esta es la memoria (puede estar vacía): {memoria}"""

# Crear una memoria nueva a partir del historial del chat y de la memoria existente, si la hay
INSTRUCCION_CREAR_MEMORIA = """"Estás reuniendo información sobre el usuario para personalizar tus respuestas.

INFORMACIÓN ACTUAL DEL USUARIO:
{memoria}

INSTRUCCIONES:
1. Revisa con atención el historial del chat que aparece abajo
2. Identifica información nueva sobre el usuario, como:
   - Datos personales (nombre, lugar donde vive)
   - Preferencias (lo que le gusta y lo que no)
   - Intereses y pasatiempos
   - Experiencias pasadas
   - Metas o planes futuros
3. Combina la información nueva con la memoria existente
4. Da a la memoria el formato de una lista con viñetas, clara
5. Si la información nueva contradice la memoria existente, conserva la versión más reciente

Recuerda: incluye solo información factual que el usuario haya dicho directamente. No hagas suposiciones ni inferencias.

Con base en el historial del chat que aparece abajo, actualiza la información del usuario:"""

def llamar_modelo(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Carga la memoria desde el Store y la usa para personalizar la respuesta del chatbot."""

    # Obtenemos la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)

    # Obtenemos el id del usuario desde la configuración
    id_usuario = configurable.id_usuario

    # Recuperamos la memoria desde el Store
    namespace = ("memoria", id_usuario)
    clave = "memoria_usuario"
    memoria_existente = store.get(namespace, clave)

    # Extraemos la memoria
    if memoria_existente:
        # El valor es un diccionario con una clave "memoria"
        contenido_memoria_existente = memoria_existente.value.get('memoria')
    else:
        contenido_memoria_existente = "No se encontró ninguna memoria."

    # Damos formato a la memoria dentro del mensaje de sistema
    mensaje_sistema = MENSAJE_SISTEMA_MODELO.format(memoria=contenido_memoria_existente)

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

    # Extraemos la memoria
    if memoria_existente:
        # El valor es un diccionario con una clave "memoria"
        contenido_memoria_existente = memoria_existente.value.get('memoria')
    else:
        contenido_memoria_existente = "No se encontró ninguna memoria."

    # Damos formato a la memoria dentro del mensaje de sistema
    mensaje_sistema = INSTRUCCION_CREAR_MEMORIA.format(memoria=contenido_memoria_existente)
    memoria_nueva = modelo.invoke([SystemMessage(content=mensaje_sistema)]+estado['messages'])

    # Sobrescribimos la memoria existente en el Store
    clave = "memoria_usuario"
    store.put(namespace, clave, {"memoria": memoria_nueva.content})

# Definimos el grafo
constructor = StateGraph(MessagesState,config_schema=configuration.Configuracion)
constructor.add_node("llamar_modelo", llamar_modelo)
constructor.add_node("escribir_memoria", escribir_memoria)
constructor.add_edge(START, "llamar_modelo")
constructor.add_edge("llamar_modelo", "escribir_memoria")
constructor.add_edge("escribir_memoria", END)
grafo = constructor.compile()