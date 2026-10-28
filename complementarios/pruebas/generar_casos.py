"""Genera, con LangGraph real, los casos que la lógica en JS de cada simulación tiene que reproducir.

Uso, desde la raíz del repositorio:

    python complementarios/pruebas/generar_casos.py

Escribe un JSON por simulación en complementarios/pruebas/casos/. Los tests de
complementarios/pruebas/logica.test.js los comparan con lo que calcula el JS.
"""

import json
import operator
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

CASOS = Path(__file__).with_name("casos")


def correr(grafo, entrada: dict, limite: int) -> dict:
    """Corre el grafo con stream_mode="values" y anota los estados y el error, si hay."""
    estados = []
    try:
        for s in grafo.stream(entrada, {"recursion_limit": limite}, stream_mode="values"):
            estados.append(dict(s))
        error = None
    except GraphRecursionError:
        error = {"tipo": "GraphRecursionError"}
    except ZeroDivisionError as e:
        error = {"tipo": "ZeroDivisionError", "mensaje": str(e)}
    return {"estados": estados, "error": error}


# --- Simulación 1: supersteps y reducers --------------------------------------


class EstadoMCD(TypedDict):
    a: int
    b: int


class EstadoConCocientes(TypedDict):
    a: int
    b: int
    cocientes: Annotated[list[int], operator.add]


class EstadoCocientesSinReducer(TypedDict):
    a: int
    b: int
    cocientes: list[int]


class EstadoNewton(TypedDict):
    x: float
    n: int


def continuar_mcd(s: dict) -> str:
    return "paso" if s["b"] != 0 else END


def paso_mcd(s: dict) -> dict:
    return {"a": s["b"], "b": s["a"] % s["b"]}


def paso_mcd_con_cociente(s: dict) -> dict:
    a, b = s["a"], s["b"]
    return {"a": b, "b": a % b, "cocientes": [a // b]}


FUNCIONES = {
    "x^2-2": (lambda x: x**2 - 2, lambda x: 2 * x),
    "x^2+1": (lambda x: x**2 + 1, lambda x: 2 * x),
}


def grafo(esquema, paso, continuar, entrada: str):
    """START → paso con la arista de `entrada`: "while" (condicional) o "do-while" (fija)."""
    constructor = StateGraph(esquema)
    constructor.add_node("paso", paso)
    if entrada == "while":
        constructor.add_conditional_edges(START, continuar, ["paso", END])
    else:
        constructor.add_edge(START, "paso")
    constructor.add_conditional_edges("paso", continuar, ["paso", END])
    return constructor.compile()


def grafo_newton(funcion: str, epsilon: float, entrada: str):
    f, df = FUNCIONES[funcion]

    def paso(s: dict) -> dict:
        x = s["x"]
        return {"x": x - f(x) / df(x), "n": s["n"] + 1}

    def continuar(s: dict) -> str:
        return "paso" if abs(f(s["x"])) >= epsilon else END

    return grafo(EstadoNewton, paso, continuar, entrada)


def casos_supersteps() -> list[dict]:
    casos = []
    for entrada in ("while", "do-while"):
        for a, b in [(1071, 462), (21, 7), (5, 0), (0, 5), (13, 8), (89, 55), (100, 75), (7, 7)]:
            for limite in (1, 2, 3, 4, 5, 25):
                for cocientes in ("ninguna", "operator.add", "sin reducer"):
                    if cocientes == "ninguna":
                        g, e = grafo(EstadoMCD, paso_mcd, continuar_mcd, entrada), {"a": a, "b": b}
                    else:
                        esquema = EstadoConCocientes if cocientes == "operator.add" else EstadoCocientesSinReducer
                        g = grafo(esquema, paso_mcd_con_cociente, continuar_mcd, entrada)
                        e = {"a": a, "b": b, "cocientes": []}
                    casos.append({
                        "algoritmo": "euclides", "entrada": entrada, "cocientes": cocientes,
                        "a": a, "b": b, "limite": limite, **correr(g, e, limite),
                    })
        for funcion in FUNCIONES:
            for x0 in (1.0, 2.0, 0.5, 3.0, -1.0, 0.001, 0.0, 10.0):
                for epsilon in (1e-10, 1e-4):
                    for limite in (3, 5, 25):
                        g = grafo_newton(funcion, epsilon, entrada)
                        casos.append({
                            "algoritmo": "newton", "entrada": entrada, "funcion": funcion,
                            "x0": x0, "epsilon": epsilon, "limite": limite,
                            **correr(g, {"x": x0, "n": 0}, limite),
                        })
    return casos


def main() -> None:
    CASOS.mkdir(exist_ok=True)
    datos = {"langgraph": version("langgraph"), "casos": casos_supersteps()}
    ruta = CASOS / "supersteps.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(ruta, len(datos["casos"]), "casos")


if __name__ == "__main__":
    main()
