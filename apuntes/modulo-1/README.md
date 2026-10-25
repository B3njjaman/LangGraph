# Módulo 1 · Introducción

Mis apuntes del módulo 1, en cinco notebooks. Siguen el orden del curso y cada uno parte de lo que armó el anterior: primero un grafo que solo junta texto, al final un agente que usa herramientas y recuerda la conversación.

| Notebook | Lecciones del curso | Qué cubre |
|---|---|---|
| [1 · El grafo más simple](01_el_grafo_mas_simple.ipynb) | 1 Motivación, 2 El grafo más simple | Estado, nodos, aristas normales y condicionales, `compile`, `invoke` y `stream`. No usa modelo |
| [2 · Mensajes y cadena](02_mensajes_y_cadena.ipynb) | 4 Cadena | Mensajes, herramientas y `bind_tools`, el estado con mensajes y el reducer `add_messages` |
| [3 · Router](03_router.ipynb) | 5 Router, 3 LangSmith Studio | `ToolNode`, `tools_condition` y cómo abrir los grafos en Studio |
| [4 · Agente](04_agente.ipynb) | 6 Agente | El ciclo ReAct: la arista de `tools` vuelve al modelo. `recursion_limit` |
| [5 · Agente con memoria](05_agente_con_memoria.ipynb) | 7 Agente con memoria | Checkpointer, hilos, `get_state` y `get_state_history` |

La lección 8, una introducción opcional al despliegue, queda para el módulo 6, que trata ese tema completo.

## Cómo ejecutarlos

Los notebooks 2 a 5 usan un modelo local con [Ollama](https://ollama.com), gratis y sin claves. Con Ollama instalado y abierto:

```bash
ollama pull qwen2.5:7b
```

Son unos 4,7 GB. Después, desde la raíz del repositorio:

```bash
python -m venv .venv
.venv\Scripts\activate          # en macOS o Linux: source .venv/bin/activate
pip install -r apuntes/requirements.txt
jupyter notebook apuntes/modulo-1
```

Cada notebook trae una celda para cambiar el modelo por `gpt-4o` de OpenAI, el que usa el curso. Con `qwen2.5:7b` en una GTX 1060, cada respuesta tarda unos segundos.
