"""Genera las figuras matemáticas animadas de la lección 1 (método de Newton para x² − 2).

Escribe tres SVG en `modulo-1/`, sin dependencias (solo la biblioteca estándar):

- `tangentes.svg`: dos pasos de Newton como tangentes a la curva.
- `babilonico.svg`: rectángulos de área 2 que se acercan a un cuadrado de lado √2.
- `error.svg`: el error de Newton en escala logarítmica, contra un método de orden 1.

Cada SVG sigue el tema claro u oscuro del navegador y se anima solo con SMIL.

Uso, desde la raíz del repositorio:

    python imagenes/figuras/generar.py
"""

import math
from pathlib import Path
from xml.sax.saxutils import escape

SALIDA = Path(__file__).parent / "modulo-1"

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# Paleta: (modo claro, modo oscuro). Es la misma de imagenes/diagramas/generar.py.
PALETA = {
    "fondo": ("#ffffff", "#0b1120"),
    "tarjeta": ("#f6f8fa", "#111a2c"),
    "borde": ("#d0d7de", "#26324a"),
    "tinta": ("#1f2328", "#e6edf3"),
    "suave": ("#57606a", "#9aa7b8"),
    "tenue": ("#8c959f", "#64748b"),
    "nodo": ("#ffffff", "#0e1626"),
    "borde-nodo": ("#aab6c5", "#3b4d6b"),
    "linea": ("#8c9bb0", "#52668a"),
    "turquesa": ("#0d9488", "#2dd4bf"),
    "turquesa-suave": ("#ccfbf1", "#0f3a3a"),
    "violeta": ("#7c3aed", "#a78bfa"),
    "violeta-suave": ("#ede9fe", "#2a2152"),
    "ambar": ("#d97706", "#fbbf24"),
    "ambar-suave": ("#fef3c7", "#3a2d0d"),
    "rosa": ("#e11d48", "#fb7185"),
    "rosa-suave": ("#ffe4e6", "#43192b"),
    "celeste": ("#0284c7", "#38bdf8"),
    "celeste-suave": ("#e0f2fe", "#0c2e48"),
    "verde": ("#16a34a", "#4ade80"),
    "verde-suave": ("#dcfce7", "#0f3220"),
}

COLORES_USADOS = ("fondo", "tinta", "suave", "tenue", "turquesa", "turquesa-suave", "violeta", "ambar")

SUPERINDICES = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def c(valor):
    """Coordenada o tiempo con pocos decimales."""
    return f"{valor:.2f}".rstrip("0").rstrip(".")


def numero(valor, decimales):
    return f"{valor:.{decimales}f}".replace(".", ",")


def cientifico(valor):
    mantisa, exponente = f"{valor:.1e}".split("e")
    return f"{mantisa.replace('.', ',')}·10{str(int(exponente)).translate(SUPERINDICES)}"


def potencia_de_diez(exponente):
    return "10" + str(exponente).translate(SUPERINDICES)


def newton(x0, pasos):
    """Iteradas de Newton para f(x) = x² − 2."""
    xs = [x0]
    for _ in range(pasos):
        xs.append(xs[-1] - (xs[-1] ** 2 - 2) / (2 * xs[-1]))
    return xs


def css():
    def reglas(indice):
        lineas = []
        for nombre in COLORES_USADOS:
            color = PALETA[nombre][indice]
            lineas.append(f".f-{nombre}{{fill:{color}}} .s-{nombre}{{stroke:{color}}}")
        lineas.append(f".halo{{stroke:{PALETA['fondo'][indice]}}}")
        return "\n".join(lineas)

    return (
        "<style>\n"
        f".sans{{font-family:{SANS}}}\n"
        f".mono{{font-family:{MONO}}}\n"
        ".halo{stroke-width:5;stroke-linejoin:round;paint-order:stroke}\n"
        + reglas(0)
        + "\n@media (prefers-color-scheme: dark) {\n"
        + reglas(1)
        + "\n}\n</style>"
    )


def svg(ancho, alto, titulo, cuerpo):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
        f'width="{ancho}" height="{alto}" role="img">\n'
        f"<title>{escape(titulo)}</title>\n{css()}\n"
        f'<rect width="{ancho}" height="{alto}" class="f-fondo"/>\n'
        f"{cuerpo}\n</svg>\n"
    )


def animar(atributo, puntos, duracion, discreto=False):
    """Un `<animate>` en bucle. `puntos` es una lista de (segundo, valor); el último valor se mantiene hasta el final."""
    puntos = list(puntos)
    if puntos[0][0] != 0:
        puntos.insert(0, (0, puntos[0][1]))
    if puntos[-1][0] != duracion:
        puntos.append((duracion, puntos[-1][1]))
    valores = ";".join(str(valor) for _, valor in puntos)
    tiempos = ";".join(f"{t / duracion:.4f}" for t, _ in puntos)
    modo = ' calcMode="discrete"' if discreto else ""
    return (
        f'<animate attributeName="{atributo}" values="{valores}" keyTimes="{tiempos}" '
        f'dur="{c(duracion)}s" repeatCount="indefinite"{modo}/>'
    )


def aparecer(segundo, duracion):
    return animar("opacity", [(0, 0), (segundo, 0), (segundo + 0.4, 1)], duracion)


def crecer(atributo, desde, hasta, inicio, fin, duracion):
    return animar(atributo, [(0, c(desde)), (inicio, c(desde)), (fin, c(hasta))], duracion)


def texto(x, y, contenido, color="tinta", tam=16, ancla="start", peso="normal", halo=False, clase="sans", hijos=""):
    clases = f"{clase} f-{color}" + (" halo" if halo else "")
    return (
        f'<text x="{c(x)}" y="{c(y)}" class="{clases}" font-size="{tam}" font-weight="{peso}" '
        f'text-anchor="{ancla}">{contenido}{hijos}</text>'
    )


def linea(x1, y1, x2, y2, color, grosor=2, punteada="", hijos=""):
    dash = f' stroke-dasharray="{punteada}"' if punteada else ""
    return (
        f'<line x1="{c(x1)}" y1="{c(y1)}" x2="{c(x2)}" y2="{c(y2)}" class="s-{color}" '
        f'stroke-width="{grosor}" stroke-linecap="round"{dash}>{hijos}</line>'
    )


def punto(x, y, color, radio=5, hijos=""):
    return f'<circle cx="{c(x)}" cy="{c(y)}" r="{radio}" class="f-{color}">{hijos}</circle>'


def poligonal(puntos, color, grosor=2, punteada=""):
    dash = f' stroke-dasharray="{punteada}"' if punteada else ""
    lista = " ".join(f"{c(x)},{c(y)}" for x, y in puntos)
    return (
        f'<polyline points="{lista}" fill="none" class="s-{color}" stroke-width="{grosor}" '
        f'stroke-linejoin="round" stroke-linecap="round"{dash}/>'
    )


def tangentes():
    ancho, alto, duracion = 680, 410, 12
    x0_g, ancho_g = 50, 600  # píxeles donde empieza y cuánto mide el eje x (de 0,6 a 2,2)

    def X(x):
        return x0_g + (x - 0.6) / 1.6 * ancho_g

    def Y(fx):
        return 60 + (2.9 - fx) * 320 / 4.6

    def f(x):
        return x * x - 2

    x0, x1, x2 = newton(1.0, 2)
    raiz = math.sqrt(2)
    eje = Y(0)
    curva = [(X(0.6 + 0.02 * i), Y(f(0.6 + 0.02 * i))) for i in range(81)]
    partes = [
        poligonal(curva, "violeta", 3),
        linea(X(0.6), eje, X(2.2), eje, "suave", 1.5),
    ]
    for marca in (1, 1.5, 2):
        partes.append(linea(X(marca), eje - 5, X(marca), eje + 5, "suave", 1.5))
    partes.append(texto(X(1), eje - 14, "x₀ = 1", "suave", 16, "middle"))
    partes.append(texto(X(1.5) - 6, eje + 28, "x₁ = 1,5", "suave", 16, "start"))
    partes.append(texto(X(2), eje + 28, "2", "suave", 16, "middle"))
    partes.append(linea(X(raiz), eje - 10, X(raiz), eje + 10, "ambar", 3))
    partes.append(texto(X(raiz), eje + 28, "√2", "ambar", 17, "middle", "bold", halo=True))
    partes.append(texto(60, 86, "f(x) = x² − 2", "violeta", 19, peso="bold"))
    partes.append(texto(60, 114, "x₁ = x₀ − f(x₀) / f′(x₀)", "suave", 16))

    vertical0 = linea(
        X(x0), Y(f(x0)), X(x0), eje, "suave", 1.5, "3 5",
        hijos=crecer("y2", Y(f(x0)), eje, 0.8, 2.0, duracion),
    )
    tangente0 = linea(
        X(x0), Y(f(x0)), X(x1), eje, "turquesa", 2.5,
        hijos=crecer("x2", X(x0), X(x1), 2.4, 4.4, duracion) + crecer("y2", Y(f(x0)), eje, 2.4, 4.4, duracion),
    )
    vertical1 = linea(
        X(x1), eje, X(x1), Y(f(x1)), "suave", 1.5, "3 5",
        hijos=crecer("y2", eje, Y(f(x1)), 5.2, 6.4, duracion),
    )
    tangente1 = linea(
        X(x1), Y(f(x1)), X(x2), eje, "turquesa", 2.5,
        hijos=crecer("x2", X(x1), X(x2), 6.8, 8.6, duracion) + crecer("y2", Y(f(x1)), eje, 6.8, 8.6, duracion),
    )
    partes += [vertical0, tangente0, vertical1, tangente1]

    partes.append(punto(X(x0), Y(f(x0)), "turquesa", 6))
    partes.append(texto(X(x0) - 10, Y(f(x0)) - 10, "(x₀, f(x₀))", "turquesa", 16, "end", halo=True))
    partes.append(punto(X(x1), eje, "turquesa", 5, aparecer(4.4, duracion)))
    partes.append(punto(X(x1), Y(f(x1)), "turquesa", 6, aparecer(6.4, duracion)))
    partes.append(punto(X(x2), eje, "turquesa", 5, aparecer(8.6, duracion)))
    etiquetas = (
        texto(X(x2) - 10, eje - 12, "x₂ ≈ √2", "turquesa", 17, "end", "bold", True)
        + texto(X(x2) - 10, eje - 34, f"a {numero(x2 - raiz, 4)} de √2", "suave", 15, "end", halo=True)
    )
    partes.append(f'<g>{etiquetas}{aparecer(8.8, duracion)}</g>')
    return svg(ancho, alto, "Dos pasos del método de Newton para f(x) = x² − 2 vistos como tangentes a la curva", "\n".join(partes))


def babilonico():
    ancho, alto, duracion = 680, 410, 11
    escala, izquierda, base = 150, 60, 380
    xs = newton(1.0, 3)
    lados = [(x, 2 / x) for x in xs]
    decimales = [(0, 0), (1, 4), (5, 5), (6, 6)]
    raiz = math.sqrt(2)
    inicios = [0, 1.8, 4.8, 7.8]  # cuándo empieza cada rectángulo a moverse hacia el siguiente
    llegadas = [0, 3.0, 6.0, 9.0]

    def puntos(valores):
        lista = [(0, valores[0])]
        for n in range(1, 4):
            lista += [(inicios[n], valores[n - 1]), (llegadas[n], valores[n])]
        return lista

    anchos = [c(x * escala) for x, _ in lados]
    altos = [c(y * escala) for _, y in lados]
    ys = [c(base - y * escala) for _, y in lados]
    rectangulo = (
        f'<rect x="{izquierda}" y="{ys[3]}" width="{anchos[3]}" height="{altos[3]}" '
        'class="f-turquesa-suave s-turquesa" stroke-width="3">'
        + animar("width", puntos(anchos), duracion)
        + animar("height", puntos(altos), duracion)
        + animar("y", puntos(ys), duracion)
        + "</rect>"
    )
    lado = raiz * escala
    cuadrado = (
        f'<rect x="{izquierda}" y="{c(base - lado)}" width="{c(lado)}" height="{c(lado)}" fill="none" '
        'class="s-ambar" stroke-width="2.5" stroke-dasharray="7 6"/>'
    )
    partes = [
        linea(izquierda - 10, base, izquierda + 250, base, "tenue", 1.5),
        cuadrado,
        rectangulo,
    ]
    cambios = [2.4, 5.4, 8.4]  # el texto cambia a mitad de cada transformación
    for n, (x, y) in enumerate(lados):
        contenido = f"n = {n} · {numero(x, decimales[n][0])} × {numero(y, decimales[n][1])}"
        if n == 0:
            puntos_texto = [(0, 1), (cambios[0], 0)]
        elif n == 3:
            puntos_texto = [(0, 0), (cambios[2], 1)]
        else:
            puntos_texto = [(0, 0), (cambios[n - 1], 1), (cambios[n], 0)]
        partes.append(
            f'<g opacity="{1 if n == 3 else 0}">'
            + texto(330, 130, contenido, "tinta", 19, peso="bold")
            + animar("opacity", puntos_texto, duracion, discreto=True)
            + "</g>"
        )
    partes += [
        texto(330, 190, "área = 2 en cada paso", "turquesa", 18, peso="bold"),
        texto(330, 224, "lado nuevo = (x + 2/x) / 2", "suave", 17),
        linea(330, 335, 366, 335, "ambar", 2.5, "7 6"),
        texto(376, 341, f"cuadrado de lado √2 ≈ {numero(raiz, 5)}", "ambar", 16),
    ]
    return svg(ancho, alto, "Método babilónico: rectángulos de área 2 que se acercan a un cuadrado de lado raíz de 2", "\n".join(partes))


def error():
    ancho, alto, duracion = 700, 470, 9.5
    izq, paso, arriba, por_decada = 130, 64, 80, 20
    errores = [abs(x - math.sqrt(2)) for x in newton(1.0, 4)]
    referencia = [errores[0] * 2 ** -n for n in range(9)]

    def X(n):
        return izq + n * paso

    def Y(valor):
        return arriba + -math.log10(valor) * por_decada

    fondo = Y(1e-16)
    derecha = X(8)
    partes = []
    for exponente in range(0, -17, -4):
        y = Y(10.0 ** exponente)
        partes.append(linea(izq, y, derecha, y, "tenue", 1, "2 5"))
        partes.append(texto(izq - 12, y + 5, potencia_de_diez(exponente), "suave", 16, "end"))
    partes.append(linea(izq, arriba, izq, fondo, "suave", 1.5))
    partes.append(linea(izq, fondo, derecha, fondo, "suave", 1.5))
    for n in range(9):
        partes.append(texto(X(n), fondo + 26, str(n), "suave", 16, "middle"))
    partes.append(texto((izq + derecha) / 2, fondo + 52, "n (número de pasos)", "suave", 16, "middle"))
    subindice = '<tspan dy="4" font-size="12">n</tspan><tspan dy="-4"> = |x</tspan><tspan dy="4" font-size="12">n</tspan><tspan dy="-4"> − √2|</tspan>'
    partes.append(texto(30, 34, "error de Newton, e", "tinta", 18, peso="bold", hijos=subindice))

    precision = Y(2.2e-16)
    partes.append(linea(izq, precision, derecha, precision, "ambar", 1.5, "10 5"))
    partes.append(texto(derecha, precision - 8, "precisión de máquina (2,2·10⁻¹⁶)", "ambar", 16, "end", halo=True))

    partes.append(poligonal([(X(n), Y(v)) for n, v in enumerate(referencia)], "violeta", 2.5, "7 6"))
    for n, v in enumerate(referencia):
        partes.append(punto(X(n), Y(v), "violeta", 3))
    partes.append(texto(derecha, 188, "orden 1:", "violeta", 16, "end", "bold", True))
    partes.append(texto(derecha, 210, "el error se divide por 2 en cada paso", "violeta", 16, "end", halo=True))

    for n, valor in enumerate(errores):
        x, y = X(n), Y(valor)
        if n == 0:
            etiqueta = texto(x + 12, y - 10, cientifico(valor), "turquesa", 16, peso="bold", halo=True)
            partes.append(punto(x, y, "turquesa", 6) + etiqueta)
            continue
        segmento = linea(X(n - 1), Y(errores[n - 1]), x, y, "turquesa", 3)
        dx, ancla = (10, "end") if n == 1 else (-8, "end")
        etiqueta = texto(x + dx, y + 25, cientifico(valor), "turquesa", 16, ancla, "bold", True)
        partes.append(f'<g>{segmento}{punto(x, y, "turquesa", 6)}{etiqueta}{aparecer(1.0 + 1.2 * n, duracion)}</g>')
    nota = (
        texto(X(4) + 26, 292, "Newton: el exponente", "turquesa", 16, peso="bold")
        + texto(X(4) + 26, 314, "casi se duplica en cada paso", "turquesa", 16, peso="bold")
    )
    partes.append(f'<g>{nota}{aparecer(6.8, duracion)}</g>')
    return svg(ancho, alto, "Error del método de Newton en escala logarítmica: el exponente casi se duplica en cada paso", "\n".join(partes))


FIGURAS = {"tangentes": tangentes, "babilonico": babilonico, "error": error}


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, construir in FIGURAS.items():
        destino = SALIDA / f"{nombre}.svg"
        contenido = construir()
        destino.write_text(contenido, encoding="utf-8")
        print(f"listo  {destino.name}  ({len(contenido.encode('utf-8')) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
