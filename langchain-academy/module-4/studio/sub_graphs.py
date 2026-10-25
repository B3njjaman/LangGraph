from operator import add
from typing import List, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

# La estructura de los registros
class Registro(TypedDict):
    id: str
    pregunta: str
    docs: Optional[List]
    respuesta: str
    nota: Optional[int]
    evaluador: Optional[str]
    feedback: Optional[str]

# Subgrafo de análisis de fallas
class EstadoAnalisisFallas(TypedDict):
    registros_limpios: List[Registro]
    fallas: List[Registro]
    resumen_fallas: str
    registros_procesados: List[str]

class EstadoAnalisisFallasSalida(TypedDict):
    resumen_fallas: str
    registros_procesados: List[str]

def obtener_fallas(estado):
    """ Obtiene los registros que contienen una falla """
    registros_limpios = estado["registros_limpios"]
    fallas = [registro for registro in registros_limpios if "nota" in registro]
    return {"fallas": fallas}

def generar_resumen(estado):
    """ Genera un resumen de las fallas """
    fallas = estado["fallas"]
    # Agregar función: resumen_fallas = resumir(fallas)
    resumen_fallas = "Mala calidad en la recuperación de la documentación de Chroma."
    return {"resumen_fallas": resumen_fallas, "registros_procesados": [f"analisis-de-fallas-en-registro-{falla['id']}" for falla in fallas]}

constructor_af = StateGraph(EstadoAnalisisFallas,output_schema=EstadoAnalisisFallasSalida)
constructor_af.add_node("obtener_fallas", obtener_fallas)
constructor_af.add_node("generar_resumen", generar_resumen)
constructor_af.add_edge(START, "obtener_fallas")
constructor_af.add_edge("obtener_fallas", "generar_resumen")
constructor_af.add_edge("generar_resumen", END)

# Subgrafo de resumen de preguntas
class EstadoResumenPreguntas(TypedDict):
    registros_limpios: List[Registro]
    resumen_preguntas: str
    informe: str
    registros_procesados: List[str]

class EstadoResumenPreguntasSalida(TypedDict):
    informe: str
    registros_procesados: List[str]

def generar_resumen(estado):
    registros_limpios = estado["registros_limpios"]
    # Agregar función: resumen = resumir(generar_resumen)
    resumen = "Las preguntas se centraron en el uso de ChatOllama y del vector store de Chroma."
    return {"resumen_preguntas": resumen, "registros_procesados": [f"resumen-en-registro-{registro['id']}" for registro in registros_limpios]}

def enviar_a_slack(estado):
    resumen_preguntas = estado["resumen_preguntas"]
    # Agregar función: informe = generar_informe(resumen_preguntas)
    informe = "foo bar baz"
    return {"informe": informe}

constructor_rp = StateGraph(EstadoResumenPreguntas,output_schema=EstadoResumenPreguntasSalida)
constructor_rp.add_node("generar_resumen", generar_resumen)
constructor_rp.add_node("enviar_a_slack", enviar_a_slack)
constructor_rp.add_edge(START, "generar_resumen")
constructor_rp.add_edge("generar_resumen", "enviar_a_slack")
constructor_rp.add_edge("enviar_a_slack", END)

# Grafo de entrada
class EstadoGrafoEntrada(TypedDict):
    registros_crudos: List[Registro]
    registros_limpios: List[Registro]
    resumen_fallas: str # Solo se genera en el subgrafo de análisis de fallas
    informe: str # Solo se genera en el subgrafo de resumen de preguntas
    registros_procesados:  Annotated[List[int], add] # Se genera en AMBOS subgrafos

def limpiar_registros(estado):
    # Obtenemos los registros
    registros_crudos = estado["registros_crudos"]
    # Limpieza de datos: registros_crudos -> docs
    registros_limpios = registros_crudos
    return {"registros_limpios": registros_limpios}

constructor_entrada = StateGraph(EstadoGrafoEntrada)
constructor_entrada.add_node("limpiar_registros", limpiar_registros)
constructor_entrada.add_node("resumir_preguntas", constructor_rp.compile())
constructor_entrada.add_node("analizar_fallas", constructor_af.compile())

constructor_entrada.add_edge(START, "limpiar_registros")
constructor_entrada.add_edge("limpiar_registros", "analizar_fallas")
constructor_entrada.add_edge("limpiar_registros", "resumir_preguntas")
constructor_entrada.add_edge("analizar_fallas", END)
constructor_entrada.add_edge("resumir_preguntas", END)

grafo = constructor_entrada.compile()
