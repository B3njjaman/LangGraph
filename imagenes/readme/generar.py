"""Genera las imágenes animadas del README, en versión clara y oscura.

    python imagenes/readme/generar.py

Solo usa la biblioteca estándar. Las animaciones son SMIL y CSS dentro de cada
SVG, sin JavaScript, para que GitHub las muestre en el README. Las fuentes son
las del sistema, porque GitHub no deja que un SVG cargue fuentes externas.
"""

from __future__ import annotations

import math
from html import escape
from pathlib import Path

CARPETA = Path(__file__).parent

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

TEMAS = {
    "oscuro": {
        "fondo1": "#0b1120", "fondo2": "#141d33", "borde": "#26324a", "puntos": "#1b2640",
        "tinta": "#e6edf3", "suave": "#9aa7b8", "tenue": "#64748b",
        "nodo": "#111a2c", "pill": "#0e1626", "borde_nodo": "#34445f", "linea": "#46587a",
        "codigo": "#0a1020",
        "turquesa": "#2dd4bf", "violeta": "#a78bfa", "ambar": "#fbbf24",
        "rosa": "#fb7185", "celeste": "#38bdf8", "verde": "#4ade80",
        "brillo": 0.55, "halo": 0.14,
    },
    "claro": {
        "fondo1": "#ffffff", "fondo2": "#f1f5fa", "borde": "#d0d7de", "puntos": "#e3e9f0",
        "tinta": "#1f2328", "suave": "#57606a", "tenue": "#8c959f",
        "nodo": "#ffffff", "pill": "#f6f8fa", "borde_nodo": "#c3cdd9", "linea": "#9aa8ba",
        "codigo": "#f6f8fa",
        "turquesa": "#0d9488", "violeta": "#7c3aed", "ambar": "#d97706",
        "rosa": "#e11d48", "celeste": "#0284c7", "verde": "#16a34a",
        "brillo": 0.32, "halo": 0.08,
    },
}

# Cada módulo tiene su color, el mismo en la ruta y en su tarjeta.
ACENTOS = ["tenue", "turquesa", "celeste", "rosa", "ambar", "violeta", "verde"]

DUR = 10  # segundos que dura un ciclo de animación
FIN = DUR - 0.8  # momento en que todo se desvanece para volver a empezar


# --- Línea de tiempo -------------------------------------------------------


def _claves(dur: float, pares: list[tuple[float, object]]) -> tuple[str, str]:
    """Convierte [(segundo, valor), ...] en keyTimes y values de SMIL."""
    pares = list(pares)
    if pares[0][0] > 0:
        pares.insert(0, (0, pares[0][1]))
    if pares[-1][0] < dur:
        pares.append((dur, pares[-1][1]))
    tiempos = ";".join(f"{min(s / dur, 1):.4f}" for s, _ in pares)
    valores = ";".join(str(v) for _, v in pares)
    return tiempos, valores


def animar(atributo: str, pares, dur: float = DUR, modo: str = "linear") -> str:
    tiempos, valores = _claves(dur, pares)
    return (
        f'<animate attributeName="{atributo}" dur="{dur}s" repeatCount="indefinite" '
        f'calcMode="{modo}" keyTimes="{tiempos}" values="{valores}"/>'
    )


def ventanas(tramos, alto: float = 1, fundido: float = 0.3) -> list[tuple[float, float]]:
    """Opacidad que sube a `alto` en cada tramo (entra, sale) y vuelve a 0."""
    pares: list[tuple[float, float]] = [(0, 0)]
    for entra, sale in tramos:
        pares += [(entra, 0), (entra + fundido, alto), (sale, alto), (sale + fundido, 0)]
    return pares


def aparecer(entra: float, sale: float = FIN, alto: float = 1) -> str:
    return animar("opacity", ventanas([(entra, sale)], alto))


class Ruta:
    """Camino de una ficha. Cada vértice queda numerado para el horario."""

    def __init__(self, x: float, y: float):
        self.d = [f"M{x:g},{y:g}"]
        self.largos = [0.0]
        self._p = (x, y)

    def a(self, x: float, y: float) -> Ruta:
        self.d.append(f"L{x:g},{y:g}")
        self._sumar(math.dist(self._p, (x, y)))
        self._p = (x, y)
        return self

    def curva(self, c1, c2, p) -> Ruta:
        p0 = self._p
        puntos = [_bezier(p0, c1, c2, p, i / 48) for i in range(49)]
        self.d.append(f"C{c1[0]:g},{c1[1]:g} {c2[0]:g},{c2[1]:g} {p[0]:g},{p[1]:g}")
        self._sumar(sum(math.dist(a, b) for a, b in zip(puntos, puntos[1:])))
        self._p = p
        return self

    def _sumar(self, largo: float) -> None:
        self.largos.append(self.largos[-1] + largo)

    def fraccion(self, vertice: int) -> float:
        return self.largos[vertice] / self.largos[-1]


def _bezier(p0, p1, p2, p3, s):
    u = 1 - s
    return tuple(u**3 * a + 3 * u * u * s * b + 3 * u * s * s * c + s**3 * d for a, b, c, d in zip(p0, p1, p2, p3))


def ficha(t: dict, color: str, ruta: Ruta, horario: list[tuple[float, int]], r: float = 7, tramos=None) -> str:
    """Un punto que recorre la ruta: horario = [(segundo, vértice), ...].

    Se dibuja debajo de los nodos, así que desaparece al entrar en uno. Si el
    camino no empieza o no termina dentro de un nodo, `tramos` dice cuándo se ve.
    """
    pares = [(s, f"{ruta.fraccion(v):.4f}") for s, v in horario]
    tiempos, puntos = _claves(DUR, pares)
    movimiento = (
        f'<animateMotion dur="{DUR}s" repeatCount="indefinite" calcMode="linear" '
        f'keyTimes="{tiempos}" keyPoints="{puntos}" path="{" ".join(ruta.d)}"/>'
    )
    opacidad = f' opacity="0">{animar("opacity", ventanas(tramos, fundido=0.1))}' if tramos else ">"
    return (
        f"<g{opacidad}{movimiento}<circle r=\"{r * 2.2:g}\" fill=\"{t[color]}\" opacity=\".45\" filter=\"url(#difuso)\"/>"
        f'<circle r="{r:g}" fill="{t[color]}"/></g>'
    )


def punta(t, x, y, desde, color) -> str:
    """Punta de flecha en (x, y), apuntando en la dirección que viene de `desde`."""
    angulo = math.atan2(y - desde[1], x - desde[0])
    vertices = [(x, y)] + [
        (x - 10 * math.cos(angulo + giro), y - 10 * math.sin(angulo + giro)) for giro in (0.45, -0.45)
    ]
    return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in vertices)}" fill="{t[color]}"/>'


# --- Piezas de dibujo ------------------------------------------------------


def ancho(texto: str, tam: float, fuente: str = "mono") -> float:
    return len(texto) * tam * (0.62 if fuente == "mono" else 0.55)


def texto(x, y, contenido, *, tam=16, color, fuente="sans", peso=400, ancla="start", extra="") -> str:
    return (
        f'<text x="{x:g}" y="{y:g}" class="{fuente}" font-size="{tam:g}" font-weight="{peso}" '
        f'fill="{color}" text-anchor="{ancla}" {extra}>{escape(contenido, quote=False)}</text>'
    )


def nodo(t, x, y, w, h, etiqueta, *, sub=None, pill=False, acento="turquesa", activo=(), tam=17) -> str:
    """Nodo centrado en (x, y). `activo` son los tramos en que se ilumina."""
    r = h / 2 if pill else 12
    x0, y0 = x - w / 2, y - h / 2
    caja = f'x="{x0:g}" y="{y0:g}" width="{w:g}" height="{h:g}" rx="{r:g}"'
    partes = []
    if activo:
        partes.append(
            f'<rect {caja} fill="{t[acento]}" opacity="0" filter="url(#difuso)">'
            f"{animar('opacity', ventanas(activo, t['brillo']))}</rect>"
        )
    partes.append(f'<rect {caja} fill="{t["pill"] if pill else t["nodo"]}" stroke="{t["borde_nodo"]}" stroke-width="1.5"/>')
    if activo:
        partes.append(
            f'<rect {caja} fill="{t[acento]}" fill-opacity=".1" stroke="{t[acento]}" stroke-width="2.5" opacity="0">'
            f"{animar('opacity', ventanas(activo))}</rect>"
        )
    centro = y - 8 if sub else y
    if etiqueta:
        partes.append(texto(x, centro, etiqueta, tam=tam, color=t["tinta"], fuente="mono", peso=600, ancla="middle", extra='dy=".35em"'))
    if sub:
        partes.append(texto(x, y + 13, sub, tam=12, color=t["suave"], fuente="mono", ancla="middle", extra='dy=".35em"'))
    return "".join(partes)


def arista(t, d, *, condicional=False, flecha=True, color="linea", ancho_linea=2) -> str:
    clase = ' class="marcha"' if condicional else ""
    punta = ' marker-end="url(#flecha)"' if flecha else ""
    return f'<path d="{d}" fill="none" stroke="{t[color]}" stroke-width="{ancho_linea}" stroke-linecap="round"{clase}{punta}/>'


def chip(t, x, y, contenido, color, *, w=None, h=30, tam=13, fuente="mono", anim="", visible=False, tinta=None) -> str:
    """Etiqueta redondeada con esquina superior izquierda en (x, y)."""
    w = w or ancho(contenido, tam, fuente) + 24
    opacidad = "" if visible else ' opacity="0"'
    return (
        f"<g{opacidad}>{anim}"
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{min(h / 2, 10):g}" fill="{t[color]}" '
        f'fill-opacity=".14" stroke="{t[color]}" stroke-opacity=".75" stroke-width="1.2"/>'
        + texto(x + w / 2, y + h / 2, contenido, tam=tam, color=tinta or t["tinta"], fuente=fuente, ancla="middle", extra='dy=".35em"')
        + "</g>"
    )


def cilindro(t, x, y_arriba, y_abajo, rx, color, activo=()) -> str:
    ry = rx * 0.2
    cuerpo = (
        f"M{x - rx:g},{y_arriba:g} L{x - rx:g},{y_abajo:g} "
        f"A{rx:g},{ry:g} 0 0 0 {x + rx:g},{y_abajo:g} L{x + rx:g},{y_arriba:g}"
    )
    partes = []
    if activo:
        partes.append(
            f'<rect x="{x - rx:g}" y="{y_arriba - ry:g}" width="{2 * rx:g}" height="{y_abajo - y_arriba + 2 * ry:g}" '
            f'rx="{ry:g}" fill="{t[color]}" opacity="0" filter="url(#difuso)">'
            f"{animar('opacity', ventanas(activo, t['brillo']))}</rect>"
        )
    partes.append(f'<path d="{cuerpo}" fill="{t["nodo"]}" stroke="{t[color]}" stroke-width="1.8"/>')
    partes.append(
        f'<ellipse cx="{x:g}" cy="{y_arriba:g}" rx="{rx:g}" ry="{ry:g}" fill="{t["pill"]}" stroke="{t[color]}" stroke-width="1.8"/>'
    )
    return "".join(partes)


def lienzo(t, w, h, titulo, cuerpo, defs="") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="titulo">
<title id="titulo">{escape(titulo, quote=False)}</title>
<style>
.sans{{font-family:{SANS}}}
.mono{{font-family:{MONO}}}
.marcha{{stroke-dasharray:6 7;animation:marcha 1.3s linear infinite}}
@keyframes marcha{{to{{stroke-dashoffset:-26}}}}
@media (prefers-reduced-motion:reduce){{.marcha{{animation:none}}}}
</style>
<defs>
<linearGradient id="fondo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t['fondo1']}"/><stop offset="1" stop-color="{t['fondo2']}"/></linearGradient>
<pattern id="puntos" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="{t['puntos']}"/></pattern>
<filter id="difuso" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="7"/></filter>
<marker id="flecha" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,1 L9,5 L0,9 z" fill="{t['linea']}"/></marker>
{defs}
</defs>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="url(#fondo)" stroke="{t['borde']}"/>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="url(#puntos)"/>
{cuerpo}
</svg>
"""


# --- Portada ---------------------------------------------------------------


def portada(t) -> str:
    """Título, una llamada a un agente que se escribe sola y el agente ejecutándola."""
    partes = [
        '<rect x="1" y="1" width="1198" height="418" rx="18" fill="url(#halo)"/>',
        texto(64, 96, "CURSO · LANGCHAIN ACADEMY", tam=14, color=t["turquesa"], fuente="mono", peso=600, extra='letter-spacing="3"'),
        texto(58, 186, "LangGraph", tam=92, color="url(#degradado-titulo)", peso=800, extra='letter-spacing="-2"'),
        texto(64, 236, "Apuntes y notebooks del curso", tam=28, color=t["tinta"], peso=600),
        texto(64, 272, "de un grafo simple a un agente desplegado", tam=20, color=t["suave"]),
    ]

    # Una llamada que se escribe letra a letra
    llamada = 'agent.invoke({"messages": "¿Cuánto es 3 × 4?"})'
    paso, x_llamada, inicio, fin_tecleo = 9.0, 122, 0.4, 2.5
    n = len(llamada)
    anchos = [(0, 0)] + [(inicio + (fin_tecleo - inicio) * i / n, i * paso) for i in range(1, n + 1)] + [(FIN + 0.5, 0)]
    partes += [
        f'<rect x="64" y="306" width="512" height="54" rx="12" fill="{t["codigo"]}" stroke="{t["borde"]}"/>',
        texto(84, 338, ">>>", tam=16, color=t["tenue"], fuente="mono"),
        f'<clipPath id="tecleo"><rect x="{x_llamada}" y="314" height="36" width="0">{animar("width", anchos, modo="discrete")}</rect></clipPath>',
        f'<g clip-path="url(#tecleo)">'
        + texto(x_llamada, 338, llamada, tam=16, color=t["tinta"], fuente="mono", extra=f'textLength="{n * paso:g}" lengthAdjust="spacingAndGlyphs"')
        + "</g>",
        f'<rect y="324" width="9" height="20" fill="{t["turquesa"]}">'
        f'{animar("x", [(s, x_llamada + w) for s, w in anchos], modo="discrete")}'
        f'<animate attributeName="opacity" values="1;0" dur="1s" calcMode="discrete" repeatCount="indefinite"/></rect>',
    ]

    # El agente: START → assistant ⇄ tools → END
    partes += [
        arista(t, "M800,98 L800,160"),
        arista(t, "M885,178 C915,140 940,140 968,176", condicional=True),
        arista(t, "M970,202 C940,240 915,240 887,204"),
        arista(t, "M800,218 L800,278", condicional=True),
        texto(927, 128, "tool_calls", tam=12, color=t["suave"], fuente="mono", ancla="middle"),
        texto(814, 254, "sin tool_calls", tam=12, color=t["suave"], fuente="mono"),
    ]
    ruta = (
        Ruta(800, 78).a(800, 98).a(800, 162).a(800, 190).a(885, 178)
        .curva((915, 140), (940, 140), (970, 178)).a(1040, 190).a(970, 202)
        .curva((940, 240), (915, 240), (885, 202)).a(800, 190).a(800, 218).a(800, 280).a(800, 300)
    )
    horario = [
        (2.8, 0), (2.9, 1), (3.25, 2), (3.4, 3), (4.2, 3), (4.35, 4), (4.9, 5), (5.05, 6),
        (5.75, 6), (5.9, 7), (6.45, 8), (6.6, 9), (7.3, 9), (7.45, 10), (7.8, 11), (7.95, 12),
    ]
    partes.append(ficha(t, "ambar", ruta, horario))
    partes += [
        nodo(t, 800, 78, 120, 40, "START", pill=True, activo=[(0.2, 2.9)], tam=15),
        nodo(t, 800, 190, 170, 56, "assistant", sub="LLM", activo=[(3.25, 4.3), (6.45, 7.4)]),
        nodo(t, 1040, 190, 140, 56, "tools", sub="multiply", activo=[(4.9, 5.85)]),
        nodo(t, 800, 300, 120, 40, "END", pill=True, activo=[(7.8, FIN)], tam=15),
    ]

    # El estado: la lista de mensajes crece con cada paso
    partes.append(texto(640, 350, "state['messages']", tam=13, color=t["suave"], fuente="mono"))
    x = 640
    for contenido, color, entra in [
        ("user · ¿3 × 4?", "celeste", 2.8),
        ("ai · multiply(3, 4)", "violeta", 4.3),
        ("tool · 12", "ambar", 5.85),
        ("ai · Es 12", "violeta", 7.4),
    ]:
        w = ancho(contenido, 12) + 20
        partes.append(chip(t, x, 362, contenido, color, w=w, tam=12, anim=aparecer(entra)))
        x += w + 10

    defs = (
        f'<linearGradient id="degradado-titulo" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{t["turquesa"]}"/><stop offset="1" stop-color="{t["violeta"]}"/></linearGradient>'
        f'<radialGradient id="halo" gradientUnits="userSpaceOnUse" cx="930" cy="190" r="460">'
        f'<stop offset="0" stop-color="{t["turquesa"]}" stop-opacity="{t["halo"] * 1.6:g}"/>'
        f'<stop offset="1" stop-color="{t["turquesa"]}" stop-opacity="0"/></radialGradient>'
    )
    return lienzo(t, 1200, 420, "LangGraph: un agente que llama a una herramienta y responde", "\n".join(partes), defs)


# --- Ruta del curso --------------------------------------------------------

MODULOS = [
    ("Puesta a punto", "entorno y claves", "17 min"),
    ("Introducción", "del grafo al agente", "51 min"),
    ("Estado y memoria", "reducers y resúmenes", "45 min"),
    ("Human-in-the-loop", "pausar y aprobar", "55 min"),
    ("Tu asistente", "paralelo, map-reduce", "61 min"),
    ("Memoria larga", "Store y Trustcall", "78 min"),
    ("Despliegue", "servidor y SDK", "49 min"),
]


def ruta_del_curso(t) -> str:
    x0, x1, y = 110, 1090, 66
    paso = (x1 - x0) / 6
    inicio, por_modulo, dur = 0.4, 1.0, 9
    partes = [
        f'<path d="M{x0},{y} L{x1},{y}" stroke="{t["borde_nodo"]}" stroke-width="4" stroke-linecap="round"/>',
        f'<path d="M{x0},{y} L{x1},{y}" stroke="url(#progreso)" stroke-width="4" stroke-linecap="round" pathLength="100" stroke-dasharray="100">'
        + animar("stroke-dashoffset", [(0, 100), (inicio, 100), (inicio + 6 * por_modulo, 0), (dur - 0.2, 0), (dur - 0.19, 100)], dur)
        + animar("opacity", [(0, 1), (dur - 0.7, 1), (dur - 0.3, 0)], dur)
        + "</path>",
    ]
    for i, (titulo, sub, minutos) in enumerate(MODULOS):
        x = x0 + i * paso
        color = t[ACENTOS[i]]
        luz = ventanas([(inicio + i * por_modulo, dur - 0.7)], fundido=0.25)
        partes += [
            f'<circle cx="{x:g}" cy="{y}" r="22" fill="{color}" opacity="0" filter="url(#difuso)">{animar("opacity", [(s, v * t["brillo"]) for s, v in luz], dur)}</circle>',
            f'<circle cx="{x:g}" cy="{y}" r="20" fill="{t["nodo"]}" stroke="{t["borde_nodo"]}" stroke-width="2.5"/>',
            f'<circle cx="{x:g}" cy="{y}" r="20" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-width="2.5" opacity="0">{animar("opacity", luz, dur)}</circle>',
            texto(x, y, str(i), tam=16, color=t["tinta"], fuente="mono", peso=700, ancla="middle", extra='dy=".35em"'),
            texto(x, 124, titulo, tam=17, color=t["tinta"], peso=600, ancla="middle"),
            texto(x, 148, sub, tam=14, color=t["suave"], ancla="middle"),
            texto(x, 176, minutos, tam=13, color=color, fuente="mono", peso=600, ancla="middle"),
        ]
    # La cabeza de la barra de progreso
    cabeza = Ruta(x0, y).a(x1, y)
    pares = [(0, "0"), (inicio, "0"), (inicio + 6 * por_modulo, "1"), (dur, "1")]
    tiempos, puntos = _claves(dur, pares)
    partes.append(
        f'<g opacity="0">{animar("opacity", [(0, 0), (inicio, 0), (inicio + 0.2, 1), (dur - 0.7, 1), (dur - 0.3, 0)], dur)}'
        f'<animateMotion dur="{dur}s" repeatCount="indefinite" calcMode="linear" keyTimes="{tiempos}" keyPoints="{puntos}" path="{" ".join(cabeza.d)}"/>'
        f'<circle r="12" fill="{t["violeta"]}" opacity=".5" filter="url(#difuso)"/><circle r="5" fill="{t["tinta"]}"/></g>'
    )
    defs = (
        f'<linearGradient id="progreso" gradientUnits="userSpaceOnUse" x1="{x0}" y1="0" x2="{x1}" y2="0">'
        f'<stop offset="0" stop-color="{t["turquesa"]}"/><stop offset="1" stop-color="{t["violeta"]}"/></linearGradient>'
    )
    return lienzo(t, 1200, 210, "Los siete módulos del curso, del 0 al 6", "\n".join(partes), defs)


# --- Tarjetas de los módulos -----------------------------------------------


def tarjeta(t, numero, titulo, lineas, cifras, diagrama, descripcion, defs="") -> str:
    acento = t[ACENTOS[numero]]
    partes = [
        texto(48, 64, f"MÓDULO {numero}", tam=15, color=acento, fuente="mono", peso=700, extra='letter-spacing="3"'),
        texto(46, 110, titulo, tam=36, color=t["tinta"], peso=800, extra='letter-spacing="-0.5"'),
    ]
    partes += [texto(48, 148 + 26 * i, linea, tam=18, color=t["suave"]) for i, linea in enumerate(lineas)]
    w = ancho(cifras, 14) + 28
    partes.append(chip(t, 48, 222, cifras, ACENTOS[numero], w=w, h=32, tam=14, visible=True))
    partes.append(diagrama)
    return lienzo(t, 1200, 290, descripcion, "\n".join(partes), defs)


def modulo_1(t) -> str:
    """El grafo más simple: una arista condicional elige entre node_2 y node_3."""
    partes = [
        arista(t, "M610,145 L656,145"),
        arista(t, "M782,135 C820,135 820,80 856,80", condicional=True),
        arista(t, "M782,155 C820,155 820,210 856,210", condicional=True),
        arista(t, "M982,80 C1020,80 1020,135 1048,135"),
        arista(t, "M982,210 C1020,210 1020,155 1048,155"),
        texto(824, 150, "decide_mood", tam=12, color=t["suave"], fuente="mono", extra='dy=".35em"'),
    ]
    for rama, y_rama, desfase in [(2, 80, 0), (3, 210, 5)]:
        ruta = (
            Ruta(560, 145).a(610, 145).a(658, 145).a(720, 145).a(782, 145 + (-10 if rama == 2 else 10))
            .curva((820, 145 + (-10 if rama == 2 else 10)), (820, y_rama), (858, y_rama)).a(920, y_rama)
            .a(982, y_rama).curva((1020, y_rama), (1020, 145 + (-10 if rama == 2 else 10)), (1050, 145 + (-10 if rama == 2 else 10)))
            .a(1100, 145)
        )
        d = desfase
        horario = [
            (d + 0.4, 0), (d + 0.55, 1), (d + 0.8, 2), (d + 0.95, 3), (d + 1.6, 3), (d + 1.75, 4),
            (d + 2.3, 5), (d + 2.45, 6), (d + 3.1, 6), (d + 3.25, 7), (d + 3.8, 8), (d + 3.95, 9),
        ]
        if d:
            horario = [(0, 0)] + horario
        partes.append(ficha(t, "turquesa", ruta, horario))
    partes += [
        nodo(t, 560, 145, 100, 40, "START", pill=True, activo=[(0.1, 0.6), (5.1, 5.6)], tam=15),
        nodo(t, 720, 145, 124, 56, "node_1", sub="+ I am", activo=[(0.8, 1.75), (5.8, 6.75)]),
        nodo(t, 920, 80, 124, 56, "node_2", sub="+ happy!", activo=[(2.3, 3.25)]),
        nodo(t, 920, 210, 124, 56, "node_3", sub="+ sad!", activo=[(7.3, 8.25)]),
        nodo(t, 1100, 145, 100, 40, "END", pill=True, activo=[(3.8, 4.7), (8.8, 9.6)], tam=15),
    ]
    return tarjeta(
        t, 1, "Introducción",
        ["Nodos, aristas y estado: del grafo", "más simple a un agente con", "herramientas y memoria."],
        "8 lecciones · 51 min", "\n".join(partes),
        "Módulo 1: un grafo con una arista condicional que elige entre dos nodos",
    )


def modulo_2(t) -> str:
    """Los mensajes se acumulan en el estado y, pasado el límite, se resumen."""
    partes = [
        texto(510, 58, 'state["messages"]', tam=13, color=t["suave"], fuente="mono"),
        texto(1160, 58, "reducer: add_messages", tam=13, color=t["celeste"], fuente="mono", ancla="end"),
    ]
    resumen_entra, corre, sale = 5.5, 5.7, FIN
    for i in range(6):
        x = 510 + 110 * i
        color = "celeste" if i % 2 == 0 else "violeta"
        etiqueta = "human" if i % 2 == 0 else "ai"
        entra = 0.5 + 0.7 * i
        if i < 4:
            anim = animar("opacity", [(0, 0), (entra, 0), (entra + 0.3, 1), (resumen_entra, 1), (resumen_entra + 0.4, 0)])
        else:
            anim = aparecer(entra) + (
                f'<animateTransform attributeName="transform" type="translate" dur="{DUR}s" repeatCount="indefinite" '
                f'keyTimes="0;{corre / DUR:.4f};{(corre + 0.5) / DUR:.4f};{(DUR - 0.1) / DUR:.4f};1" '
                f'values="0 0;0 0;-220 0;-220 0;0 0" calcMode="linear"/>'
            )
        partes.append(chip(t, x, 72, etiqueta, color, w=100, h=36, tam=14, anim=anim))
    partes += [
        chip(t, 510, 72, "resumen de 4 mensajes", "ambar", w=210, h=36, tam=13, anim=aparecer(resumen_entra + 0.2, sale)),
        f'<g opacity="0">{aparecer(resumen_entra, 7.6)}'
        + texto(725, 132, "RemoveMessage × 4", tam=12, color=t["rosa"], fuente="mono", ancla="middle")
        + "</g>",
        arista(t, "M735,205 L804,205", condicional=True),
        arista(t, "M995,205 L1048,205"),
        texto(770, 172, "si es larga", tam=12, color=t["suave"], fuente="mono", ancla="middle"),
    ]
    ruta = Ruta(640, 205).a(735, 205).a(805, 205).a(900, 205).a(995, 205).a(1050, 205).a(1100, 205)
    horario = [(4.6, 0), (4.75, 1), (5.05, 2), (5.2, 3), (6.3, 3), (6.45, 4), (6.75, 5), (6.9, 6)]
    partes.append(ficha(t, "celeste", ruta, horario))
    partes += [
        nodo(t, 640, 205, 190, 52, "conversation", acento="celeste", activo=[(0.4, 4.7)]),
        nodo(t, 900, 205, 190, 52, "summarize", acento="celeste", activo=[(5.05, 6.4)]),
        nodo(t, 1100, 205, 100, 40, "END", pill=True, acento="celeste", activo=[(6.75, FIN)], tam=15),
    ]
    return tarjeta(
        t, 2, "Estado y memoria",
        ["Esquemas de estado, reducers y", "cómo recortar o resumir una", "conversación larga."],
        "6 lecciones · 45 min", "\n".join(partes),
        "Módulo 2: los mensajes se acumulan en el estado y los más antiguos se resumen",
    )


def modulo_3(t) -> str:
    """Un breakpoint detiene el grafo antes de tools hasta que una persona aprueba."""
    partes = [
        arista(t, "M600,110 L638,110"),
        arista(t, "M790,110 L883,110"),
        arista(t, "M1015,110 L1053,110"),
        texto(838, 72, "interrupt_before", tam=12, color=t["rosa"], fuente="mono", ancla="middle"),
        f'<rect x="834" y="88" width="8" height="44" rx="4" fill="{t["rosa"]}" opacity=".45">'
        + animar("opacity", [(0, 0.45), (2.05, 0.45), (2.1, 1), (2.6, 0.5), (3.1, 1), (3.6, 0.5), (4.1, 1), (4.3, 1), (4.6, 0.12), (FIN, 0.12), (DUR - 0.2, 0.45)])
        + "</rect>",
        f'<g opacity="0">{aparecer(2.6, 5.0)}'
        f'<rect x="723" y="156" width="230" height="40" rx="12" fill="{t["nodo"]}" stroke="{t["rosa"]}" stroke-width="1.4"/>'
        + texto(838, 176, "¿Ejecutar la herramienta?", tam=15, color=t["tinta"], ancla="middle", extra='dy=".35em"')
        + "</g>",
        chip(t, 778, 206, "aprobar ✓", "verde", w=120, h=30, tam=13, anim=aparecer(3.6, 5.0)),
        # Línea de checkpoints, uno por paso
        f'<path d="M550,262 L1100,262" stroke="{t["borde_nodo"]}" stroke-width="2" stroke-dasharray="2 6" stroke-linecap="round"/>',
        texto(540, 242, "checkpoints", tam=12, color=t["suave"], fuente="mono"),
    ]
    for x, entra, color in [(550, 0.4, "turquesa"), (715, 1.0, "turquesa"), (838, 2.1, "rosa"), (950, 4.9, "turquesa"), (1100, 6.0, "turquesa")]:
        partes.append(f'<circle cx="{x}" cy="262" r="7" fill="{t[color]}" opacity="0">{aparecer(entra)}</circle>')
    partes += [
        f'<circle cx="838" cy="262" r="12" fill="{t["violeta"]}" opacity="0" filter="url(#difuso)">{animar("opacity", ventanas([(7.8, 8.8)], t["brillo"] * 1.6))}</circle>',
        f'<path d="M1100,252 C1050,200 890,200 842,250" fill="none" stroke="{t["violeta"]}" stroke-width="2.2" '
        f'pathLength="100" stroke-dasharray="100" stroke-dashoffset="100" opacity="0">'
        + animar("stroke-dashoffset", [(0, 100), (7.0, 100), (7.8, 0), (DUR - 0.1, 0), (DUR, 100)])
        + aparecer(7.0)
        + "</path>",
        f'<g opacity="0">{aparecer(7.75)}{punta(t, 842, 250, (890, 200), "violeta")}</g>',
        f'<g opacity="0">{aparecer(7.4)}' + texto(970, 196, "time travel", tam=13, color=t["violeta"], fuente="mono", peso=600, ancla="middle") + "</g>",
    ]
    ruta = Ruta(550, 110).a(600, 110).a(640, 110).a(715, 110).a(790, 110).a(828, 110).a(885, 110).a(950, 110).a(1015, 110).a(1055, 110).a(1100, 110)
    horario = [
        (0.4, 0), (0.55, 1), (0.8, 2), (0.95, 3), (1.6, 3), (1.75, 4), (2.05, 5), (4.4, 5),
        (4.65, 6), (4.8, 7), (5.4, 7), (5.55, 8), (5.8, 9), (5.95, 10),
    ]
    partes.append(ficha(t, "rosa", ruta, horario))
    partes += [
        nodo(t, 550, 110, 100, 40, "START", pill=True, activo=[(0.1, 0.6)], tam=15),
        nodo(t, 715, 110, 150, 52, "assistant", acento="rosa", activo=[(0.8, 1.75)]),
        nodo(t, 950, 110, 130, 52, "tools", acento="rosa", activo=[(4.65, 5.55)]),
        nodo(t, 1100, 110, 90, 40, "END", pill=True, acento="rosa", activo=[(5.8, FIN)], tam=15),
    ]
    return tarjeta(
        t, 3, "Human-in-the-loop",
        ["Streaming, breakpoints, editar el", "estado con feedback humano y", "volver atrás en el tiempo."],
        "5 lecciones · 55 min", "\n".join(partes),
        "Módulo 3: el grafo se detiene antes de usar una herramienta hasta que una persona lo aprueba",
    )


def modulo_4(t) -> str:
    """Send() reparte el tema entre tres entrevistas en paralelo y el informe las junta."""
    filas = [62, 145, 228]
    partes = [arista(t, "M585,145 L613,145")]
    for y in filas:
        partes.append(arista(t, f"M745,145 C785,145 785,{y} 823,{y}", condicional=True))
        partes.append(arista(t, f"M975,{y} C1005,{y} 1005,145 1028,145"))
    partes += [
        texto(680, 104, "Send() × 3", tam=12, color=t["ambar"], fuente="mono", peso=600, ancla="middle"),
        texto(1090, 96, "reduce", tam=12, color=t["suave"], fuente="mono", ancla="middle"),
    ]
    inicio = Ruta(540, 145).a(585, 145).a(615, 145).a(680, 145)
    partes.append(ficha(t, "ambar", inicio, [(0.4, 0), (0.55, 1), (0.75, 2), (0.9, 3)]))
    terminos = [3.4, 3.9, 3.1]
    for y, termina in zip(filas, terminos):
        ruta = (
            Ruta(680, 145).a(745, 145).curva((785, 145), (785, y), (825, y)).a(900, y)
            .a(975, y).curva((1005, y), (1005, 145), (1030, 145)).a(1090, 145)
        )
        horario = [(1.8, 0), (1.95, 1), (2.5, 2), (2.65, 3), (termina, 3), (termina + 0.15, 4), (termina + 0.65, 5), (termina + 0.8, 6)]
        partes.append(ficha(t, "ambar", ruta, horario, r=6))
    partes += [
        nodo(t, 540, 145, 90, 40, "tema", pill=True, acento="ambar", activo=[(0.1, 0.6)], tam=15),
        nodo(t, 680, 145, 130, 52, "analistas", acento="ambar", activo=[(0.75, 1.95)]),
    ]
    for i, (y, termina) in enumerate(zip(filas, terminos), start=1):
        partes.append(nodo(t, 900, y, 150, 50, f"entrevista {i}", acento="ambar", activo=[(2.5, termina + 0.15)], tam=15))
    partes.append(nodo(t, 1090, 145, 120, 76, "", acento="ambar", activo=[(4.55, FIN)]))
    partes.append(texto(1090, 127, "informe", tam=17, color=t["tinta"], fuente="mono", peso=600, ancla="middle", extra='dy=".35em"'))
    for i, largo in enumerate([70, 58, 46]):
        y = 151 + 11 * i
        entra = 4.8 + 0.4 * i
        partes.append(
            f'<path d="M1055,{y} L{1055 + largo},{y}" stroke="{t["ambar"]}" stroke-width="3" stroke-linecap="round" '
            f'pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">'
            + animar("stroke-dashoffset", [(0, 100), (entra, 100), (entra + 0.5, 0), (DUR - 0.1, 0), (DUR, 100)])
            + "</path>"
        )
    return tarjeta(
        t, 4, "Tu asistente",
        ["Nodos en paralelo, sub-grafos y", "map-reduce, juntos en un", "asistente de investigación."],
        "4 lecciones · 61 min", "\n".join(partes),
        "Módulo 4: un tema se reparte entre tres entrevistas en paralelo y un informe las junta",
    )


def modulo_5(t) -> str:
    """Lo que se guarda en el Store desde un hilo se recupera en otro."""
    partes = [
        texto(500, 50, 'hilo 1 · thread_id="1"', tam=12, color=t["suave"], fuente="mono"),
        chip(t, 500, 62, "Me gusta mucho andar en bici", "celeste", w=240, h=36, tam=15, fuente="sans", anim=aparecer(0.4)),
        texto(500, 150, 'hilo 2 · thread_id="2"', tam=12, color=t["suave"], fuente="mono"),
        chip(t, 500, 162, "¿Qué hago este fin de semana?", "celeste", w=246, h=36, tam=15, fuente="sans", anim=aparecer(3.6)),
        chip(t, 540, 208, "Una ruta en bici por el cerro", "violeta", w=246, h=36, tam=15, fuente="sans", anim=aparecer(5.4)),
        arista(t, "M744,80 C830,80 900,88 966,108", condicional=True, flecha=False, color="violeta", ancho_linea=1.6),
        arista(t, "M968,200 C900,214 850,226 792,226", condicional=True, flecha=False, color="violeta", ancho_linea=1.6),
        texto(850, 70, "store.put", tam=12, color=t["violeta"], fuente="mono", peso=600, ancla="middle"),
        texto(884, 250, "store.search", tam=12, color=t["violeta"], fuente="mono", peso=600, ancla="middle"),
    ]
    # Las fichas salen de un chip translúcido, así que se encienden y apagan con `tramos`.
    escribe = Ruta(744, 80).curva((830, 80), (900, 88), (966, 108)).a(1050, 150)
    partes.append(ficha(t, "violeta", escribe, [(1.1, 0), (2.0, 1), (2.15, 2)], r=6, tramos=[(1.0, 2.1)]))
    lee = Ruta(1050, 150).a(968, 200).curva((900, 214), (850, 226), (792, 226))
    partes.append(ficha(t, "violeta", lee, [(4.3, 0), (4.45, 1), (5.3, 2)], r=6, tramos=[(4.3, 5.25)]))
    partes += [
        cilindro(t, 1050, 86, 214, 82, "violeta", activo=[(2.0, 3.0), (4.2, 5.0)]),
        texto(1050, 128, "Store", tam=20, color=t["tinta"], peso=700, ancla="middle"),
        texto(1050, 150, '(user_id, "memories")', tam=11, color=t["suave"], fuente="mono", ancla="middle"),
        chip(t, 977, 168, "le gusta el ciclismo", "violeta", w=146, h=28, tam=13, fuente="sans", anim=aparecer(2.3)),
    ]
    return tarjeta(
        t, 5, "Memoria a largo plazo",
        ["Memoria que sobrevive entre", "hilos con el Store, perfiles y", "colecciones con Trustcall."],
        "5 lecciones · 78 min", "\n".join(partes),
        "Módulo 5: un recuerdo guardado en el Store desde una conversación se usa en otra",
    )


def modulo_6(t) -> str:
    """Un cliente manda dos mensajes seguidos y el servidor encola el segundo."""
    clientes = [("SDK", 95), ("Studio", 150), ("RemoteGraph", 205)]
    partes = []
    for nombre, y in clientes:
        partes.append(arista(t, f"M640,{y} C670,{y} 670,150 698,150", flecha=False, color="borde_nodo", ancho_linea=1.6))
    partes += [
        arista(t, "M960,105 L1017,105", condicional=True, flecha=False, color="verde", ancho_linea=1.6),
        arista(t, "M960,213 L1017,213", condicional=True, flecha=False, color="verde", ancho_linea=1.6),
    ]
    # Todas las fichas empiezan y terminan escondidas dentro de una caja.
    for entra in (0.4, 2.0):
        ruta = Ruta(580, 95).a(640, 95).curva((670, 95), (670, 150), (700, 150)).a(760, 150)
        partes.append(ficha(t, "verde", ruta, [(entra, 0), (entra + 0.1, 1), (entra + 0.55, 2), (entra + 0.7, 3)], r=6))
    for y, salidas in [(213, (1.3, 1.8, 2.6, 5.0, 5.5, 6.1)), (105, (2.2, 5.9))]:
        for sale in salidas:
            flujo = Ruta(930, y).a(1047, y)
            partes.append(ficha(t, "verde", flujo, [(sale, 0), (sale + 0.45, 1)], r=4))
    for nombre, y in clientes:
        partes.append(nodo(t, 580, y, 120, 34, nombre, pill=True, acento="verde", activo=[(0.2, 0.8), (1.8, 2.4)] if nombre == "SDK" else (), tam=13))
    partes += [
        f'<rect x="700" y="40" width="260" height="220" rx="14" fill="{t["nodo"]}" stroke="{t["verde"]}" stroke-width="1.8"/>',
        texto(830, 66, "LangGraph Server", tam=17, color=t["tinta"], peso=700, ancla="middle"),
        chip(t, 716, 80, "assistant · task_maistro", "violeta", w=228, h=28, tam=12, visible=True),
        texto(718, 134, "runs del hilo", tam=11, color=t["suave"], fuente="mono"),
        # run 1: en curso → listo
        chip(t, 716, 144, "run 1 · en curso", "verde", w=228, h=28, tam=12, anim=aparecer(1.0, 4.6)),
        chip(t, 716, 144, "run 1 · listo ✓", "tenue", w=228, h=28, tam=12, anim=aparecer(4.6)),
        # run 2: en cola → en curso
        chip(t, 716, 180, "run 2 · en cola", "ambar", w=228, h=28, tam=12, anim=aparecer(2.6, 4.6)),
        chip(t, 716, 180, "run 2 · en curso", "verde", w=228, h=28, tam=12, anim=aparecer(4.6)),
        f'<g opacity="0">{aparecer(2.6, 4.6)}' + texto(830, 230, "double texting → enqueue", tam=11, color=t["rosa"], fuente="mono", peso=600, ancla="middle") + "</g>",
        cilindro(t, 1075, 82, 128, 58, "verde", activo=[(2.5, 3.0), (6.2, 6.7)]),
        texto(1075, 112, "Postgres", tam=15, color=t["tinta"], peso=700, ancla="middle"),
        texto(1075, 160, "checkpoints", tam=11, color=t["suave"], fuente="mono", ancla="middle"),
        cilindro(t, 1075, 190, 236, 58, "verde", activo=[(1.6, 3.0), (5.3, 6.5)]),
        texto(1075, 220, "Redis", tam=15, color=t["tinta"], peso=700, ancla="middle"),
        texto(1075, 268, "streaming", tam=11, color=t["suave"], fuente="mono", ancla="middle"),
    ]
    return tarjeta(
        t, 6, "Despliegue",
        ["Del notebook a una API: servidor,", "SDK, double texting y", "assistants versionados."],
        "5 lecciones · 49 min", "\n".join(partes),
        "Módulo 6: el servidor de LangGraph encola un segundo mensaje mientras termina el primero",
    )


PIEZAS = {
    "portada": portada,
    "ruta": ruta_del_curso,
    "modulo-1": modulo_1,
    "modulo-2": modulo_2,
    "modulo-3": modulo_3,
    "modulo-4": modulo_4,
    "modulo-5": modulo_5,
    "modulo-6": modulo_6,
}


def main() -> None:
    for nombre, dibujar in PIEZAS.items():
        for tema, colores in TEMAS.items():
            archivo = CARPETA / f"{nombre}-{tema}.svg"
            archivo.write_text(dibujar(colores), encoding="utf-8")
            print(archivo.relative_to(CARPETA.parent.parent))


if __name__ == "__main__":
    main()
