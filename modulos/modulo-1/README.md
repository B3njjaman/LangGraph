# Módulo 1 · Introducción

Proyecto del módulo: un agente de cálculo simbólico. Parte como un grafo sin modelo de lenguaje y termina como un agente con memoria que deriva, integra y resuelve ecuaciones con SymPy.

Cada concepto se presenta como definición, propiedad y código.

| Lección | Del curso | Qué construye | Dónde corre |
|---|---|---|---|
| [1 · Grafo sin modelo](01_grafo_sin_modelo.ipynb) | Simple graph | El método de Newton como grafo: esquema, estado, nodo, reducer, aristas, supersteps y terminación | CPU |
| 2 · Mensajes y herramientas *(próximamente)* | Chain | `add_messages` como operación sobre listas, herramientas de SymPy, `tool_call` | Kaggle |
| 3 · Router *(próximamente)* | Router | El modelo decide una vez: grafo acíclico | Kaggle |
| 4 · Agente *(próximamente)* | Agent | El ciclo `tools → modelo` y el límite de supersteps | Kaggle |
| 5 · Agente con memoria *(próximamente)* | Agent memory | El hilo como sucesión de estados, `get_state_history` | Kaggle |

## Cómo ejecutar la lección 1

No necesita GPU ni claves. Desde la raíz del repositorio:

```bash
python -m venv .venv
.venv\Scripts\activate          # en macOS o Linux: source .venv/bin/activate
pip install -r modulos/requirements.txt
jupyter notebook modulos/modulo-1
```

El dibujo del grafo usa el servicio mermaid.ink, así que esa celda necesita internet. Las lecciones 2 a 5 usan un modelo de lenguaje y corren en Kaggle; sus instrucciones llegan con ellas.
