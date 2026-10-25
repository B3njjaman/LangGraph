import operator
from pydantic import BaseModel, Field
from typing import Annotated, List
from typing_extensions import TypedDict

from langchain_community.document_loaders import WikipediaLoader
from langchain_tavily import TavilySearch  # actualizado 1.0
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, get_buffer_string
from langchain_openai import ChatOpenAI

from langgraph.constants import Send
from langgraph.graph import END, MessagesState, START, StateGraph

### LLM

llm = ChatOpenAI(model="gpt-4o", temperature=0)

### Esquema

class Analista(BaseModel):
    afiliacion: str = Field(
        description="Afiliación principal del analista.",
    )
    nombre: str = Field(
        description="Nombre del analista."
    )
    rol: str = Field(
        description="Rol del analista en el contexto del tema.",
    )
    descripcion: str = Field(
        description="Descripción del enfoque, las preocupaciones y las motivaciones del analista.",
    )
    @property
    def persona(self) -> str:
        return f"Nombre: {self.nombre}\nRol: {self.rol}\nAfiliación: {self.afiliacion}\nDescripción: {self.descripcion}\n"

class Perspectivas(BaseModel):
    analistas: List[Analista] = Field(
        description="Lista completa de analistas con sus roles y afiliaciones.",
    )

class EstadoGenerarAnalistas(TypedDict):
    tema: str # Tema de investigación
    max_analistas: int # Número de analistas
    feedback_humano_analistas: str # Feedback humano
    analistas: List[Analista] # Analistas que hacen las preguntas

class EstadoEntrevista(MessagesState):
    max_turnos: int # Número de turnos de la conversación
    contexto: Annotated[list, operator.add] # Documentos fuente
    analista: Analista # Analista que hace las preguntas
    entrevista: str # Transcripción de la entrevista
    secciones: list # Clave final que duplicamos en el estado externo para la API Send()

class ConsultaBusqueda(BaseModel):
    consulta_busqueda: str = Field(None, description="Consulta de búsqueda para la recuperación.")

class EstadoGrafoInvestigacion(TypedDict):
    tema: str # Tema de investigación
    max_analistas: int # Número de analistas
    feedback_humano_analistas: str # Feedback humano
    analistas: List[Analista] # Analistas que hacen las preguntas
    secciones: Annotated[list, operator.add] # Clave para la API Send()
    introduccion: str # Introducción del informe final
    contenido: str # Contenido del informe final
    conclusion: str # Conclusión del informe final
    informe_final: str # Informe final

### Nodos y aristas

instrucciones_analista="""Tu tarea es crear un conjunto de personas de analistas de IA. Sigue estas instrucciones con atención:

1. Primero, revisa el tema de investigación:
{tema}

2. Examina el feedback editorial que se haya entregado (es opcional) para guiar la creación de los analistas:

{feedback_humano_analistas}

3. Determina los temas más interesantes a partir de los documentos y / o del feedback anteriores.

4. Elige los {max_analistas} temas principales.

5. Asigna un analista a cada tema."""

def crear_analistas(estado: EstadoGenerarAnalistas):

    """ Crea los analistas """

    tema=estado['tema']
    max_analistas=estado['max_analistas']
    feedback_humano_analistas=estado.get('feedback_humano_analistas', '')

    # Forzamos una salida estructurada
    llm_estructurado = llm.with_structured_output(Perspectivas)

    # Mensaje de sistema
    mensaje_sistema = instrucciones_analista.format(tema=tema,
                                                            feedback_humano_analistas=feedback_humano_analistas,
                                                            max_analistas=max_analistas)

    # Generamos los analistas
    analistas = llm_estructurado.invoke([SystemMessage(content=mensaje_sistema)]+[HumanMessage(content="Genera el conjunto de analistas.")])

    # Escribimos la lista de analistas en el estado
    return {"analistas": analistas.analistas}

def feedback_humano(estado: EstadoGenerarAnalistas):
    """ Nodo que no hace nada y en el que se debe interrumpir """
    pass

# Generamos la pregunta del analista
instrucciones_pregunta = """Eres un analista encargado de entrevistar a un experto para aprender sobre un tema específico.

Tu objetivo es llegar a ideas interesantes y específicas relacionadas con tu tema.

1. Interesantes: ideas que a la gente le resulten sorprendentes o poco obvias.

2. Específicas: ideas que eviten las generalidades e incluyan ejemplos concretos del experto.

Este es tu tema de enfoque y tu conjunto de objetivos: {objetivos}

Comienza presentándote con un nombre que encaje con tu persona y luego haz tu pregunta.

Sigue haciendo preguntas para profundizar y afinar tu comprensión del tema.

Cuando estés satisfecho con tu comprensión, termina la entrevista con: "¡Muchas gracias por tu ayuda!"

Recuerda mantenerte en el personaje durante toda tu respuesta, reflejando la persona y los objetivos que se te dieron."""

def generar_pregunta(estado: EstadoEntrevista):

    """ Nodo para generar una pregunta """

    # Obtenemos el estado
    analista = estado["analista"]
    mensajes = estado["messages"]

    # Generamos la pregunta
    mensaje_sistema = instrucciones_pregunta.format(objetivos=analista.persona)
    pregunta = llm.invoke([SystemMessage(content=mensaje_sistema)]+mensajes)

    # Escribimos los mensajes en el estado
    return {"messages": [pregunta]}

# Redacción de la consulta de búsqueda
instrucciones_busqueda = SystemMessage(content=f"""Se te entregará una conversación entre un analista y un experto.

Tu objetivo es generar una consulta bien estructurada para usar en una recuperación y / o una búsqueda web relacionada con la conversación.

Primero, analiza la conversación completa.

Presta especial atención a la última pregunta que hizo el analista.

Convierte esta última pregunta en una consulta de búsqueda web bien estructurada""")

def buscar_web(estado: EstadoEntrevista):

    """ Recupera documentos con una búsqueda web """

    # Búsqueda
    busqueda_tavily = TavilySearch(max_results=3)

    # Consulta de búsqueda
    llm_estructurado = llm.with_structured_output(ConsultaBusqueda)
    consulta_busqueda = llm_estructurado.invoke([instrucciones_busqueda]+estado['messages'])

    # Búsqueda
    datos = busqueda_tavily.invoke({"query": consulta_busqueda.consulta_busqueda})
    docs_busqueda = datos.get("results", datos)

     # Formato
    docs_busqueda_formateados = "\n\n---\n\n".join(
        [
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in docs_busqueda
        ]
    )

    return {"contexto": [docs_busqueda_formateados]}

def buscar_wikipedia(estado: EstadoEntrevista):

    """ Recupera documentos de Wikipedia """

    # Consulta de búsqueda
    llm_estructurado = llm.with_structured_output(ConsultaBusqueda)
    consulta_busqueda = llm_estructurado.invoke([instrucciones_busqueda]+estado['messages'])

    # Búsqueda
    docs_busqueda = WikipediaLoader(query=consulta_busqueda.consulta_busqueda,
                                  load_max_docs=2).load()

     # Formato
    docs_busqueda_formateados = "\n\n---\n\n".join(
        [
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content}\n</Document>'
            for doc in docs_busqueda
        ]
    )

    return {"contexto": [docs_busqueda_formateados]}

# Generamos la respuesta del experto
instrucciones_respuesta = """Eres un experto al que está entrevistando un analista.

Esta es el área de enfoque del analista: {objetivos}.

Tu objetivo es responder una pregunta que hace el entrevistador.

Para responder la pregunta, usa este contexto:

{contexto}

Al responder las preguntas, sigue estas pautas:

1. Usa solo la información entregada en el contexto.

2. No agregues información externa ni hagas suposiciones más allá de lo que el contexto dice de forma explícita.

3. El contexto incluye las fuentes al comienzo de cada documento.

4. Incluye esas fuentes en tu respuesta, junto a cada afirmación relevante. Por ejemplo, para la fuente n.º 1 usa [1].

5. Enumera tus fuentes en orden al final de tu respuesta. [1] Fuente 1, [2] Fuente 2, etc.

6. Si la fuente es: <Document source="assistant/docs/llama3_1.pdf" page="7"/>' entonces solo escribe:

[1] assistant/docs/llama3_1.pdf, página 7

Y omite también los corchetes y el encabezado Document source en tu cita."""

def generar_respuesta(estado: EstadoEntrevista):

    """ Nodo para responder una pregunta """

    # Obtenemos el estado
    analista = estado["analista"]
    mensajes = estado["messages"]
    contexto = estado["contexto"]

    # Respondemos la pregunta
    mensaje_sistema = instrucciones_respuesta.format(objetivos=analista.persona, contexto=contexto)
    respuesta = llm.invoke([SystemMessage(content=mensaje_sistema)]+mensajes)

    # Indicamos que el mensaje viene del experto
    respuesta.name = "experto"

    # Lo agregamos al estado
    return {"messages": [respuesta]}

def guardar_entrevista(estado: EstadoEntrevista):

    """ Guarda la entrevista """

    # Obtenemos los mensajes
    mensajes = estado["messages"]

    # Convertimos la entrevista en un string
    entrevista = get_buffer_string(mensajes)

    # La guardamos en la clave entrevista
    return {"entrevista": entrevista}

def enrutar_mensajes(estado: EstadoEntrevista,
                   nombre: str = "experto"):

    """ Enruta entre pregunta y respuesta """

    # Obtenemos los mensajes
    mensajes = estado["messages"]
    max_turnos = estado.get('max_turnos',2)

    # Contamos las respuestas del experto
    num_respuestas = len(
        [m for m in mensajes if isinstance(m, AIMessage) and m.name == nombre]
    )

    # Terminamos si el experto respondió más veces que el máximo de turnos
    if num_respuestas >= max_turnos:
        return 'guardar_entrevista'

    # Este router se ejecuta después de cada par pregunta - respuesta
    # Tomamos la última pregunta para ver si señala el fin de la conversación
    ultima_pregunta = mensajes[-2]

    if "Muchas gracias por tu ayuda" in ultima_pregunta.content:
        return 'guardar_entrevista'
    return "hacer_pregunta"

# Escribimos un resumen de la entrevista (una sección del informe final)
instrucciones_escritor_seccion = """Eres un escritor técnico experto.

Tu tarea es crear una sección breve y fácil de digerir de un informe, a partir de un conjunto de documentos fuente.

1. Analiza el contenido de los documentos fuente:
- El nombre de cada documento fuente está al comienzo del documento, junto a la etiqueta <Document.

2. Crea una estructura de informe con formato markdown:
- Usa ## para el título de la sección
- Usa ### para los encabezados de las subsecciones

3. Escribe el informe siguiendo esta estructura:
a. Título (encabezado ##)
b. Resumen (encabezado ###)
c. Fuentes (encabezado ###)

4. Haz que tu título sea atractivo, según el área de enfoque del analista:
{enfoque}

5. Para la sección de resumen:
- Comienza el resumen con antecedentes / contexto general relacionado con el área de enfoque del analista
- Destaca lo novedoso, interesante o sorprendente de las ideas obtenidas en la entrevista
- Crea una lista numerada de los documentos fuente, a medida que los uses
- No menciones los nombres de los entrevistadores ni de los expertos
- Apunta a un máximo de unas 400 palabras
- Usa fuentes numeradas en tu informe (por ejemplo, [1], [2]) según la información de los documentos fuente

6. En la sección de Fuentes:
- Incluye todas las fuentes usadas en tu informe
- Entrega los enlaces completos a los sitios web relevantes o las rutas específicas de los documentos
- Separa cada fuente con un salto de línea. Usa dos espacios al final de cada línea para crear un salto de línea en Markdown.
- Se verá así:

### Fuentes
[1] Enlace o nombre del documento
[2] Enlace o nombre del documento

7. Asegúrate de combinar las fuentes. Por ejemplo, esto no es correcto:

[3] https://ai.meta.com/blog/meta-llama-3-1/
[4] https://ai.meta.com/blog/meta-llama-3-1/

No debe haber fuentes repetidas. Debe quedar simplemente así:

[3] https://ai.meta.com/blog/meta-llama-3-1/

8. Revisión final:
- Asegúrate de que el informe siga la estructura requerida
- No incluyas ningún preámbulo antes del título del informe
- Comprueba que se hayan seguido todas las pautas"""

def escribir_seccion(estado: EstadoEntrevista):

    """ Nodo para escribir una sección """

    # Obtenemos el estado
    entrevista = estado["entrevista"]
    contexto = estado["contexto"]
    analista = estado["analista"]

    # Escribimos la sección con los documentos fuente reunidos en la entrevista (contexto) o con la entrevista misma (entrevista)
    mensaje_sistema = instrucciones_escritor_seccion.format(enfoque=analista.descripcion)
    seccion = llm.invoke([SystemMessage(content=mensaje_sistema)]+[HumanMessage(content=f"Usa esta fuente para escribir tu sección: {contexto}")])

    # La agregamos al estado
    return {"secciones": [seccion.content]}

# Agregamos los nodos y las aristas
constructor_entrevista = StateGraph(EstadoEntrevista)
constructor_entrevista.add_node("hacer_pregunta", generar_pregunta)
constructor_entrevista.add_node("buscar_web", buscar_web)
constructor_entrevista.add_node("buscar_wikipedia", buscar_wikipedia)
constructor_entrevista.add_node("responder_pregunta", generar_respuesta)
constructor_entrevista.add_node("guardar_entrevista", guardar_entrevista)
constructor_entrevista.add_node("escribir_seccion", escribir_seccion)

# Flujo
constructor_entrevista.add_edge(START, "hacer_pregunta")
constructor_entrevista.add_edge("hacer_pregunta", "buscar_web")
constructor_entrevista.add_edge("hacer_pregunta", "buscar_wikipedia")
constructor_entrevista.add_edge("buscar_web", "responder_pregunta")
constructor_entrevista.add_edge("buscar_wikipedia", "responder_pregunta")
constructor_entrevista.add_conditional_edges("responder_pregunta", enrutar_mensajes,['hacer_pregunta','guardar_entrevista'])
constructor_entrevista.add_edge("guardar_entrevista", "escribir_seccion")
constructor_entrevista.add_edge("escribir_seccion", END)

def iniciar_entrevistas(estado: EstadoGrafoInvestigacion):

    """ Arista condicional que inicia todas las entrevistas con la API Send() o vuelve a crear_analistas """

    # Revisamos si hay feedback humano
    feedback_humano_analistas=estado.get('feedback_humano_analistas','aprobar')
    if feedback_humano_analistas.lower() != 'aprobar':
        # Volvemos a crear_analistas
        return "crear_analistas"

    # Si no, lanzamos las entrevistas en paralelo con la API Send()
    else:
        tema = estado["tema"]
        return [Send("hacer_entrevista", {"analista": analista,
                                           "messages": [HumanMessage(
                                               content=f"¿Entonces dijiste que estabas escribiendo un artículo sobre {tema}?"
                                           )
                                                       ]}) for analista in estado["analistas"]]

# Escribimos un informe a partir de las entrevistas
instrucciones_escritor_informe = """Eres un escritor técnico que crea un informe sobre este tema general:

{tema}

Tienes un equipo de analistas. Cada analista hizo dos cosas:

1. Realizó una entrevista con un experto sobre un subtema específico.
2. Redactó sus hallazgos en un memo.

Tu tarea:

1. Recibirás una colección de memos de tus analistas.
2. Piensa con cuidado en las ideas de cada memo.
3. Consolídalas en un resumen general claro que enlace las ideas centrales de todos los memos.
4. Resume los puntos centrales de cada memo en una sola narrativa coherente.

Para dar formato a tu informe:

1. Usa formato markdown.
2. No incluyas preámbulo en el informe.
3. No uses subtítulos.
4. Comienza tu informe con un único encabezado de título: ## Hallazgos
5. No menciones los nombres de ningún analista en tu informe.
6. Conserva las citas de los memos, que estarán anotadas entre corchetes, por ejemplo [1] o [2].
7. Crea una lista final y consolidada de fuentes y agrégala en una sección de Fuentes con el encabezado `## Fuentes`.
8. Enumera tus fuentes en orden y sin repetirlas.

[1] Fuente 1
[2] Fuente 2

Estos son los memos de tus analistas para construir tu informe:

{contexto}"""

def escribir_informe(estado: EstadoGrafoInvestigacion):

    """ Nodo para escribir el cuerpo del informe final """

    # Conjunto completo de secciones
    secciones = estado["secciones"]
    tema = estado["tema"]

    # Unimos todas las secciones
    secciones_formateadas = "\n\n".join([f"{seccion}" for seccion in secciones])

    # Resumimos las secciones en un informe final
    mensaje_sistema = instrucciones_escritor_informe.format(tema=tema, contexto=secciones_formateadas)
    informe = llm.invoke([SystemMessage(content=mensaje_sistema)]+[HumanMessage(content=f"Escribe un informe a partir de estos memos.")])
    return {"contenido": informe.content}

# Escribimos la introducción o la conclusión
instrucciones_intro_conclusion = """Eres un escritor técnico que está terminando un informe sobre {tema}

Se te entregarán todas las secciones del informe.

Tu trabajo es escribir una introducción o una conclusión clara y atractiva.

El usuario te indicará si debes escribir la introducción o la conclusión.

No incluyas preámbulo en ninguna de las dos secciones.

Apunta a unas 100 palabras, que presenten de forma clara un adelanto (en la introducción) o un repaso (en la conclusión) de todas las secciones del informe.

Usa formato markdown.

Para tu introducción, crea un título atractivo y usa el encabezado # para el título.

Para tu introducción, usa ## Introducción como encabezado de la sección.

Para tu conclusión, usa ## Conclusión como encabezado de la sección.

Estas son las secciones en las que debes basarte para escribir: {secciones_formateadas}"""

def escribir_introduccion(estado: EstadoGrafoInvestigacion):

    """ Nodo para escribir la introducción """

    # Conjunto completo de secciones
    secciones = estado["secciones"]
    tema = estado["tema"]

    # Unimos todas las secciones
    secciones_formateadas = "\n\n".join([f"{seccion}" for seccion in secciones])

    # Resumimos las secciones en un informe final

    instrucciones = instrucciones_intro_conclusion.format(tema=tema, secciones_formateadas=secciones_formateadas)
    intro = llm.invoke([instrucciones]+[HumanMessage(content=f"Escribe la introducción del informe")])
    return {"introduccion": intro.content}

def escribir_conclusion(estado: EstadoGrafoInvestigacion):

    """ Nodo para escribir la conclusión """

    # Conjunto completo de secciones
    secciones = estado["secciones"]
    tema = estado["tema"]

    # Unimos todas las secciones
    secciones_formateadas = "\n\n".join([f"{seccion}" for seccion in secciones])

    # Resumimos las secciones en un informe final

    instrucciones = instrucciones_intro_conclusion.format(tema=tema, secciones_formateadas=secciones_formateadas)
    conclusion = llm.invoke([instrucciones]+[HumanMessage(content=f"Escribe la conclusión del informe")])
    return {"conclusion": conclusion.content}

def finalizar_informe(estado: EstadoGrafoInvestigacion):

    """ Este es el paso "reduce": reunimos todas las secciones, las combinamos y reflexionamos sobre ellas para escribir la introducción y la conclusión """

    # Guardamos el informe final completo
    contenido = estado["contenido"]
    if contenido.startswith("## Hallazgos"):
        contenido = contenido.removeprefix("## Hallazgos")
    if "## Fuentes" in contenido:
        try:
            contenido, fuentes = contenido.split("\n## Fuentes\n")
        except:
            fuentes = None
    else:
        fuentes = None

    informe_final = estado["introduccion"] + "\n\n---\n\n" + contenido + "\n\n---\n\n" + estado["conclusion"]
    if fuentes is not None:
        informe_final += "\n\n## Fuentes\n" + fuentes
    return {"informe_final": informe_final}

# Agregamos los nodos y las aristas
constructor = StateGraph(EstadoGrafoInvestigacion)
constructor.add_node("crear_analistas", crear_analistas)
constructor.add_node("feedback_humano", feedback_humano)
constructor.add_node("hacer_entrevista", constructor_entrevista.compile())
constructor.add_node("escribir_informe",escribir_informe)
constructor.add_node("escribir_introduccion",escribir_introduccion)
constructor.add_node("escribir_conclusion",escribir_conclusion)
constructor.add_node("finalizar_informe",finalizar_informe)

# Lógica
constructor.add_edge(START, "crear_analistas")
constructor.add_edge("crear_analistas", "feedback_humano")
constructor.add_conditional_edges("feedback_humano", iniciar_entrevistas, ["crear_analistas", "hacer_entrevista"])
constructor.add_edge("hacer_entrevista", "escribir_informe")
constructor.add_edge("hacer_entrevista", "escribir_introduccion")
constructor.add_edge("hacer_entrevista", "escribir_conclusion")
constructor.add_edge(["escribir_conclusion", "escribir_informe", "escribir_introduccion"], "finalizar_informe")
constructor.add_edge("finalizar_informe", END)

# Compilamos
grafo = constructor.compile(interrupt_before=['feedback_humano'])
