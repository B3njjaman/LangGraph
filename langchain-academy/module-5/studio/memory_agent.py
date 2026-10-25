import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from trustcall import create_extractor

from typing import Literal, Optional, TypedDict

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import merge_message_runs
from langchain_core.messages import SystemMessage, HumanMessage

from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

import configuration

## Utilidades

# Inspeccionamos las llamadas a herramientas de Trustcall
class Espia:
    def __init__(self):
        self.herramientas_llamadas = []

    def __call__(self, ejecucion):
        q = [ejecucion]
        while q:
            r = q.pop()
            if r.child_runs:
                q.extend(r.child_runs)
            if r.run_type == "chat_model":
                self.herramientas_llamadas.append(
                    r.outputs["generations"][0][0]["message"]["kwargs"]["tool_calls"]
                )

# Extraemos información de las llamadas a herramientas, tanto de los parches como de las memorias nuevas, en Trustcall
def extraer_info_herramientas(llamadas_herramientas, nombre_esquema="Memoria"):
    """Extrae información de las llamadas a herramientas, tanto de los parches como de las memorias nuevas.

    Args:
        llamadas_herramientas: Lista de llamadas a herramientas del modelo
        nombre_esquema: Nombre de la herramienta del esquema (por ejemplo, "Memoria", "Tarea", "Perfil")
    """

    # Inicializamos la lista de cambios
    cambios = []

    for grupo_llamadas in llamadas_herramientas:
        for llamada in grupo_llamadas:
            if llamada['name'] == 'PatchDoc':
                cambios.append({
                    'tipo': 'actualizacion',
                    'id_documento': llamada['args']['json_doc_id'],
                    'ediciones_planeadas': llamada['args']['planned_edits'],
                    'valor': llamada['args']['patches'][0]['value']
                })
            elif llamada['name'] == nombre_esquema:
                cambios.append({
                    'tipo': 'nueva',
                    'valor': llamada['args']
                })

    # Damos formato a los resultados como un único string
    partes_resultado = []
    for cambio in cambios:
        if cambio['tipo'] == 'actualizacion':
            partes_resultado.append(
                f"Documento {cambio['id_documento']} actualizado:\n"
                f"Plan: {cambio['ediciones_planeadas']}\n"
                f"Contenido agregado: {cambio['valor']}"
            )
        else:
            partes_resultado.append(
                f"Se creó {nombre_esquema} nueva:\n"
                f"Contenido: {cambio['valor']}"
            )

    return "\n\n".join(partes_resultado)

## Definición de los esquemas

# Esquema del perfil de usuario
class Perfil(BaseModel):
    """Este es el perfil del usuario con el que estás conversando"""
    nombre: Optional[str] = Field(description="El nombre del usuario", default=None)
    ubicacion: Optional[str] = Field(description="La ubicación del usuario", default=None)
    trabajo: Optional[str] = Field(description="El trabajo del usuario", default=None)
    conexiones: list[str] = Field(
        description="Conexiones personales del usuario, como familiares, amigos o compañeros de trabajo",
        default_factory=list
    )
    intereses: list[str] = Field(
        description="Intereses que tiene el usuario",
        default_factory=list
    )

# Esquema de las tareas
class Tarea(BaseModel):
    tarea: str = Field(description="La tarea que hay que completar.")
    tiempo_estimado: Optional[int] = Field(description="Tiempo estimado para completar la tarea (minutos).")
    fecha_limite: Optional[datetime] = Field(
        description="Fecha en que la tarea debe estar completada (si corresponde)",
        default=None
    )
    soluciones: list[str] = Field(
        description="Lista de soluciones específicas y accionables (por ejemplo, ideas concretas, proveedores de servicios u opciones concretas relevantes para completar la tarea)",
        min_items=1,
        default_factory=list
    )
    situacion: Literal["sin empezar", "en curso", "hecha", "archivada"] = Field(
        description="Situación actual de la tarea",
        default="sin empezar"
    )

## Inicializamos el modelo y las herramientas

# Herramienta para actualizar la memoria
class ActualizarMemoria(TypedDict):
    """ Decisión sobre qué tipo de memoria actualizar """
    tipo_actualizacion: Literal['usuario', 'tarea', 'instrucciones']

# Inicializamos el modelo
modelo = ChatOpenAI(model="gpt-4o", temperature=0)

## Creamos los extractores de Trustcall para actualizar el perfil de usuario y la lista de tareas
extractor_perfil = create_extractor(
    modelo,
    tools=[Perfil],
    tool_choice="Perfil",
)

## Prompts

# Instrucción del chatbot para elegir qué actualizar y qué herramientas llamar
MENSAJE_SISTEMA_MODELO = """Eres un chatbot útil.

Estás diseñado para ser un compañero del usuario, ayudándolo a llevar el registro de su lista de tareas.

Tienes una memoria a largo plazo que lleva el registro de tres cosas:
1. El perfil del usuario (información general sobre él)
2. La lista de tareas del usuario
3. Instrucciones generales para actualizar la lista de tareas

Este es el perfil actual del usuario (puede estar vacío si aún no se ha reunido información):
<perfil_usuario>
{perfil_usuario}
</perfil_usuario>

Esta es la lista de tareas actual (puede estar vacía si aún no se han agregado tareas):
<tareas>
{tareas}
</tareas>

Estas son las preferencias actuales indicadas por el usuario para actualizar la lista de tareas (pueden estar vacías si aún no ha indicado ninguna):
<instrucciones>
{instrucciones}
</instrucciones>

Estas son tus instrucciones para razonar sobre los mensajes del usuario:

1. Razona con cuidado sobre los mensajes del usuario tal como se presentan a continuación.

2. Decide si hay que actualizar alguna parte de tu memoria a largo plazo:
- Si el usuario entregó información personal, actualiza su perfil llamando a la herramienta ActualizarMemoria con el tipo `usuario`
- Si se mencionan tareas, actualiza la lista de tareas llamando a la herramienta ActualizarMemoria con el tipo `tarea`
- Si el usuario indicó preferencias sobre cómo actualizar la lista de tareas, actualiza las instrucciones llamando a la herramienta ActualizarMemoria con el tipo `instrucciones`

3. Cuando corresponda, dile al usuario que actualizaste tu memoria:
- No le digas al usuario que actualizaste su perfil
- Dile al usuario cuando actualices la lista de tareas
- No le digas al usuario que actualizaste las instrucciones

4. Ante la duda, actualiza la lista de tareas. No hace falta pedir permiso explícito.

5. Responde de forma natural al usuario después de llamar a una herramienta para guardar memorias, o si no se llamó a ninguna herramienta."""

# Instrucción de Trustcall
INSTRUCCION_TRUSTCALL = """Reflexiona sobre la siguiente interacción.

Usa las herramientas disponibles para conservar las memorias necesarias sobre el usuario.

Usa llamadas a herramientas en paralelo para manejar las actualizaciones y las inserciones al mismo tiempo.

Hora del sistema: {hora}"""

# Instrucciones para actualizar la lista de tareas
INSTRUCCIONES_CREAR = """Reflexiona sobre la siguiente interacción.

A partir de esta interacción, actualiza tus instrucciones sobre cómo actualizar los elementos de la lista de tareas. Usa cualquier feedback del usuario para actualizar cómo le gusta que se agreguen los elementos, etc.

Tus instrucciones actuales son:

<instrucciones_actuales>
{instrucciones_actuales}
</instrucciones_actuales>"""

## Definición de los nodos

def task_mAIstro(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Carga las memorias desde el Store y las usa para personalizar la respuesta del chatbot."""

    # Obtenemos el id del usuario desde la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)
    id_usuario = configurable.id_usuario

   # Recuperamos la memoria del perfil desde el Store
    namespace = ("perfil", id_usuario)
    memorias = store.search(namespace)
    if memorias:
        perfil_usuario = memorias[0].value
    else:
        perfil_usuario = None

    # Recuperamos las memorias de tareas desde el Store
    namespace = ("tarea", id_usuario)
    memorias = store.search(namespace)
    tareas = "\n".join(f"{mem.value}" for mem in memorias)

    # Recuperamos las instrucciones personalizadas
    namespace = ("instrucciones", id_usuario)
    memorias = store.search(namespace)
    if memorias:
        instrucciones = memorias[0].value
    else:
        instrucciones = ""

    mensaje_sistema = MENSAJE_SISTEMA_MODELO.format(perfil_usuario=perfil_usuario, tareas=tareas, instrucciones=instrucciones)

    # Respondemos usando la memoria y el historial del chat
    respuesta = modelo.bind_tools([ActualizarMemoria], parallel_tool_calls=False).invoke([SystemMessage(content=mensaje_sistema)]+estado["messages"])

    return {"messages": [respuesta]}

def actualizar_perfil(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflexiona sobre el historial del chat y actualiza la colección de memorias."""

    # Obtenemos el id del usuario desde la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)
    id_usuario = configurable.id_usuario

    # Definimos el namespace de las memorias
    namespace = ("perfil", id_usuario)

    # Recuperamos las memorias más recientes como contexto
    elementos_existentes = store.search(namespace)

    # Damos formato a las memorias existentes para el extractor de Trustcall
    nombre_herramienta = "Perfil"
    memorias_existentes = ([(elemento_existente.key, nombre_herramienta, elemento_existente.value)
                            for elemento_existente in elementos_existentes]
                            if elementos_existentes
                            else None
                          )

    # Combinamos el historial del chat y la instrucción
    INSTRUCCION_TRUSTCALL_FORMATEADA=INSTRUCCION_TRUSTCALL.format(hora=datetime.now().isoformat())
    mensajes_actualizados=list(merge_message_runs(messages=[SystemMessage(content=INSTRUCCION_TRUSTCALL_FORMATEADA)] + estado["messages"][:-1]))

    # Invocamos el extractor
    resultado = extractor_perfil.invoke({"messages": mensajes_actualizados,
                                         "existing": memorias_existentes})

    # Guardamos en el Store las memorias de Trustcall
    for r, meta_r in zip(resultado["responses"], resultado["response_metadata"]):
        store.put(namespace,
                  meta_r.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )
    llamadas_herramientas = estado['messages'][-1].tool_calls
    # Devolvemos un mensaje de herramienta que confirma la actualización
    return {"messages": [{"role": "tool", "content": "perfil actualizado", "tool_call_id":llamadas_herramientas[0]['id']}]}

def actualizar_tareas(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflexiona sobre el historial del chat y actualiza la colección de memorias."""

    # Obtenemos el id del usuario desde la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)
    id_usuario = configurable.id_usuario

    # Definimos el namespace de las memorias
    namespace = ("tarea", id_usuario)

    # Recuperamos las memorias más recientes como contexto
    elementos_existentes = store.search(namespace)

    # Damos formato a las memorias existentes para el extractor de Trustcall
    nombre_herramienta = "Tarea"
    memorias_existentes = ([(elemento_existente.key, nombre_herramienta, elemento_existente.value)
                            for elemento_existente in elementos_existentes]
                            if elementos_existentes
                            else None
                          )

    # Combinamos el historial del chat y la instrucción
    INSTRUCCION_TRUSTCALL_FORMATEADA=INSTRUCCION_TRUSTCALL.format(hora=datetime.now().isoformat())
    mensajes_actualizados=list(merge_message_runs(messages=[SystemMessage(content=INSTRUCCION_TRUSTCALL_FORMATEADA)] + estado["messages"][:-1]))

    # Inicializamos el espía para tener visibilidad de las llamadas a herramientas que hace Trustcall
    espia = Espia()

    # Creamos el extractor de Trustcall para actualizar la lista de tareas
    extractor_tareas = create_extractor(
    modelo,
    tools=[Tarea],
    tool_choice=nombre_herramienta,
    enable_inserts=True
    ).with_listeners(on_end=espia)

    # Invocamos el extractor
    resultado = extractor_tareas.invoke({"messages": mensajes_actualizados,
                                         "existing": memorias_existentes})

    # Guardamos en el Store las memorias de Trustcall
    for r, meta_r in zip(resultado["responses"], resultado["response_metadata"]):
        store.put(namespace,
                  meta_r.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )

    # Respondemos a la llamada a herramienta hecha en task_mAIstro, confirmando la actualización
    llamadas_herramientas = estado['messages'][-1].tool_calls

    # Extraemos los cambios hechos por Trustcall y los agregamos al ToolMessage que se devuelve a task_mAIstro
    mensaje_actualizacion_tareas = extraer_info_herramientas(espia.herramientas_llamadas, nombre_herramienta)
    return {"messages": [{"role": "tool", "content": mensaje_actualizacion_tareas, "tool_call_id":llamadas_herramientas[0]['id']}]}

def actualizar_instrucciones(estado: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflexiona sobre el historial del chat y actualiza la colección de memorias."""

    # Obtenemos el id del usuario desde la configuración
    configurable = configuration.Configuracion.from_runnable_config(config)
    id_usuario = configurable.id_usuario

    namespace = ("instrucciones", id_usuario)

    memoria_existente = store.get(namespace, "instrucciones_usuario")

    # Damos formato a la memoria dentro del mensaje de sistema
    mensaje_sistema = INSTRUCCIONES_CREAR.format(instrucciones_actuales=memoria_existente.value if memoria_existente else None)
    memoria_nueva = modelo.invoke([SystemMessage(content=mensaje_sistema)]+estado['messages'][:-1] + [HumanMessage(content="Por favor, actualiza las instrucciones según la conversación")])

    # Sobrescribimos la memoria existente en el Store
    clave = "instrucciones_usuario"
    store.put(namespace, clave, {"memoria": memoria_nueva.content})
    llamadas_herramientas = estado['messages'][-1].tool_calls
    # Devolvemos un mensaje de herramienta que confirma la actualización
    return {"messages": [{"role": "tool", "content": "instrucciones actualizadas", "tool_call_id":llamadas_herramientas[0]['id']}]}

# Arista condicional
def enrutar_mensaje(estado: MessagesState, config: RunnableConfig, store: BaseStore) -> Literal[END, "actualizar_tareas", "actualizar_instrucciones", "actualizar_perfil"]:

    """Reflexiona sobre las memorias y el historial del chat para decidir si hay que actualizar la colección de memorias."""
    mensaje = estado['messages'][-1]
    if len(mensaje.tool_calls) ==0:
        return END
    else:
        llamada_herramienta = mensaje.tool_calls[0]
        if llamada_herramienta['args']['tipo_actualizacion'] == "usuario":
            return "actualizar_perfil"
        elif llamada_herramienta['args']['tipo_actualizacion'] == "tarea":
            return "actualizar_tareas"
        elif llamada_herramienta['args']['tipo_actualizacion'] == "instrucciones":
            return "actualizar_instrucciones"
        else:
            raise ValueError

# Creamos el grafo + todos los nodos
constructor = StateGraph(MessagesState, config_schema=configuration.Configuracion)

# Definimos el flujo del proceso de extracción de memorias
constructor.add_node(task_mAIstro)
constructor.add_node(actualizar_tareas)
constructor.add_node(actualizar_perfil)
constructor.add_node(actualizar_instrucciones)

# Definimos el flujo
constructor.add_edge(START, "task_mAIstro")
constructor.add_conditional_edges("task_mAIstro", enrutar_mensaje)
constructor.add_edge("actualizar_tareas", "task_mAIstro")
constructor.add_edge("actualizar_perfil", "task_mAIstro")
constructor.add_edge("actualizar_instrucciones", "task_mAIstro")

# Compilamos el grafo
grafo = constructor.compile()