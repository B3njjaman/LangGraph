# Módulo 1 · Introducción

Proyecto del módulo: un agente de cálculo simbólico. Parte como un grafo sin modelo de lenguaje y termina como un agente con memoria que deriva, integra y resuelve ecuaciones con SymPy.

Cada concepto se presenta como definición, propiedad y código, con diagramas animados del grafo y figuras de la matemática que hay detrás.

<img src="../../imagenes/diagramas/modulo-1/ruta.svg" alt="Las cinco lecciones del módulo con su grafo: 1, START → paso → END con la arista c que vuelve a paso; 2, START → modelo → END con un tool_call; 3, el router, donde el modelo va a tools o a END y tools termina; 4, el agente, con el ciclo modelo ⇄ tools; 5, el mismo agente con un checkpoint por superstep" width="100%">

| Lección | Qué construye | Dónde corre |
|---|---|---|
| [1 · Grafo sin modelo](01_grafo_sin_modelo.ipynb) | Un algoritmo como grafo: el algoritmo de Euclides del código al diagrama de flujo y a LangGraph, y con él esquema, estado, nodo, reducer, aristas, supersteps y terminación. Después, el método de Newton con el mismo grafo. Con 11 diagramas (8 animados), 3 figuras y dos profundizaciones: Newton como método babilónico (la ecuación de Pell y la fracción continua de √2) y lo que ejecuta `compile` (Pregel y canales) | CPU |
| 2 · Mensajes y herramientas *(próximamente)* | `add_messages` como operación sobre listas, herramientas de SymPy, `tool_call` | Kaggle |
| 3 · Router *(próximamente)* | El modelo decide una vez: grafo acíclico | Kaggle |
| 4 · Agente *(próximamente)* | El ciclo `tools → modelo` y el límite de supersteps | Kaggle |
| 5 · Agente con memoria *(próximamente)* | El hilo como sucesión de estados, `get_state_history` | Kaggle |

## Cómo ejecutar la lección 1

No necesita GPU ni claves. Desde la raíz del repositorio:

```bash
python -m venv .venv
.venv\Scripts\activate          # en macOS o Linux: source .venv/bin/activate
pip install -r modulos/requirements.txt
jupyter notebook
```

En el navegador, abrir `modulos/modulo-1/01_grafo_sin_modelo.ipynb`. Jupyter tiene que partir en la raíz del repositorio: las imágenes están en `imagenes/`, y si se abre directo en `modulos/modulo-1` no las puede servir.

El dibujo del grafo usa el servicio mermaid.ink, así que esa celda necesita internet. Las lecciones 2 a 5 usan un modelo de lenguaje y corren en Kaggle; sus instrucciones llegan con ellas.

## Imágenes

Los diagramas de flujo se escriben en [D2](https://d2lang.com) (fuentes en [`imagenes/diagramas/fuentes/modulo-1/`](../../imagenes/diagramas/fuentes/modulo-1/)) y las figuras se dibujan con [`imagenes/figuras/generar.py`](../../imagenes/figuras/generar.py), que solo usa la biblioteca estándar. Todos siguen el modo claro u oscuro del navegador. Para regenerarlos, desde la raíz:

```bash
python imagenes/diagramas/generar.py modulo-1    # necesita D2 0.9 o más nuevo
python imagenes/figuras/generar.py
```
