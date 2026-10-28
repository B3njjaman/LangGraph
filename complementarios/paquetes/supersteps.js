// Generado por complementarios/empaquetar.mjs desde escenas/supersteps.js. No se edita a mano.
(() => {
"use strict";
const modulos = {};

// ── logica/grafo.js
modulos["logica/grafo.js"] = (() => {
// Ejecución de un grafo de estado por supersteps, con la semántica de LangGraph 1.2.17.
// Es la parte de las simulaciones que no dibuja: se prueba en Node contra LangGraph real
// (complementarios/pruebas/logica.test.js).

const START = "START";
const END = "END";

/** Un error que en Python lanzaría el código de un nodo, con su tipo y su mensaje. */
class ErrorPython extends Error {
  constructor(tipo, mensaje) {
    super(mensaje);
    this.tipo = tipo;
  }
}

/**
 * Un grafo es un objeto con tres partes:
 *   claves:  { k: { reducer?: (v, w) => v', inicial?: valor } }   el esquema
 *   nodos:   { nombre: (s) => u }                                 φ : S → U
 *   aristas: { START | nombre: { fija: destino } | { condicional: (s) => destino } }
 * Los estados y las actualizaciones son objetos planos; un nodo devuelve solo las claves que escribe.
 */

/** s∅: el estado parcial con el valor inicial de cada clave con reducer y nada más. */
function estadoVacio(grafo) {
  const s = {};
  for (const [k, def] of Object.entries(grafo.claves)) {
    if (def.reducer && "inicial" in def) s[k] = JSON.parse(JSON.stringify(def.inicial));
  }
  return s;
}

/**
 * s ⊕ u₁ ⊕ … ⊕ uₘ: las actualizaciones de un mismo superstep. Una clave con reducer combina
 * cada valor en orden; una clave sin reducer se reemplaza, y dos escrituras a ella en el mismo
 * superstep son un error (InvalidUpdateError en LangGraph).
 */
function aplicar(grafo, s, actualizaciones) {
  const nuevo = { ...s };
  const escritas = new Set();
  for (const u of actualizaciones) {
    for (const [k, w] of Object.entries(u)) {
      const def = grafo.claves[k];
      if (!def) continue;
      if (def.reducer) {
        nuevo[k] = k in nuevo ? def.reducer(nuevo[k], w) : w;
      } else {
        if (escritas.has(k)) throw new ErrorPython("InvalidUpdateError", `la clave ${k} recibió dos valores en un superstep`);
        nuevo[k] = w;
      }
      escritas.add(k);
    }
  }
  return nuevo;
}

/** Los destinos de las aristas que salen de `origen`, evaluadas sobre el estado `s`. */
function destinos(grafo, origen, s) {
  const arista = grafo.aristas[origen];
  if (!arista) return [];
  return [arista.fija ?? arista.condicional(s)];
}

/**
 * Corre el grafo desde `entrada`. Devuelve los supersteps hechos y el error, si hubo:
 *   pasos[k] = { k, nodos, actualizaciones, antes, estado, siguientes, ramas }
 * `pasos.map(p => p.estado)` es lo que entrega stream(entrada, stream_mode="values").
 *
 * El superstep 0 es el de START: s₀ = s∅ ⊕ entrada. En cada superstep k ≥ 1 corren los nodos
 * elegidos por las aristas, todos sobre el mismo s_{k-1}. Después de cerrar el superstep k,
 * si k ≥ limite, la ejecución se corta con GraphRecursionError aunque ya no quede nada por
 * correr: así lo hace LangGraph, y por eso hacen falta tantos supersteps como `recursion_limit`.
 */
function ejecutar(grafo, entrada, { limite = 10007 } = {}) {
  const pasos = [];
  let s = aplicar(grafo, estadoVacio(grafo), [entrada]);
  let ramas = [{ origen: START, destino: destinos(grafo, START, s)[0] }];
  pasos.push({ k: 0, nodos: [START], actualizaciones: [entrada], antes: null, estado: s, ramas, siguientes: activos(ramas) });

  for (let k = 0; ; ) {
    if (k >= limite) return { pasos, error: { tipo: "GraphRecursionError", mensaje: mensajeLimite(limite) } };
    const siguientes = pasos[k].siguientes;
    if (siguientes.length === 0) return { pasos, error: null };
    k += 1;
    const antes = s;
    let actualizaciones;
    try {
      actualizaciones = siguientes.map((n) => grafo.nodos[n](antes));
      s = aplicar(grafo, antes, actualizaciones);
    } catch (e) {
      if (!(e instanceof ErrorPython)) throw e;
      return { pasos, error: { tipo: e.tipo, mensaje: e.message, k, nodos: siguientes } };
    }
    // Cada rama lee el estado anterior más la escritura de su propio nodo. Con un solo nodo
    // por superstep, como en estas simulaciones, eso es s_k.
    ramas = siguientes.flatMap((n, i) =>
      destinos(grafo, n, aplicar(grafo, antes, [actualizaciones[i]])).map((destino) => ({ origen: n, destino })),
    );
    pasos.push({ k, nodos: siguientes, actualizaciones, antes, estado: s, ramas, siguientes: activos(ramas) });
  }
}

function activos(ramas) {
  return [...new Set(ramas.map((r) => r.destino).filter((d) => d !== END))];
}

function mensajeLimite(limite) {
  return `Recursion limit of ${limite} reached without hitting a stop condition.`;
}
return { START, END, ErrorPython, aplicar, ejecutar, mensajeLimite };
})();

// ── logica/repr.js
modulos["logica/repr.js"] = (() => {
// Valores escritos como los escribe Python, para que la traza se lea igual que en el notebook.

/** repr de un float de Python: 1.0 y no 1; 1e-07 y no 1e-7. */
function reprFloat(x) {
  if (Number.isNaN(x)) return "nan";
  if (!Number.isFinite(x)) return x > 0 ? "inf" : "-inf";
  if (Number.isInteger(x) && Math.abs(x) < 1e16) return x.toFixed(1);
  return String(x).replace(/e([+-])(\d)$/, "e$10$2");
}

/** repr de un valor según el tipo de su clave ("int", "float" o "list"). */
function repr(valor, tipo) {
  if (Array.isArray(valor)) return `[${valor.map((v) => repr(v, "int")).join(", ")}]`;
  if (tipo === "float") return reprFloat(valor);
  return String(valor);
}

/** repr de un estado: {'a': 21, 'b': 0}, con las claves en el orden del esquema, como Python. */
function reprDict(d, claves) {
  const orden = Object.keys(claves).filter((k) => k in d);
  const partes = orden.map((k) => `'${k}': ${repr(d[k], claves[k].tipo)}`);
  return `{${partes.join(", ")}}`;
}
return { reprFloat, repr, reprDict };
})();

// ── logica/supersteps.js
modulos["logica/supersteps.js"] = (() => {
const { END, ErrorPython, START } = modulos["logica/grafo.js"];
// Los grafos de la lección 1: Euclides y Newton, con la arista de entrada como `while` o `do-while`.



const concatenar = (v, w) => v.concat(w); // operator.add sobre listas

/** Aristas de un bucle: START → paso (condicional o fija) y paso → paso | END. */
function aristasDeBucle(continuar, entrada) {
  return {
    [START]: entrada === "while" ? { condicional: continuar } : { fija: "paso" },
    paso: { condicional: continuar },
  };
}

/**
 * Euclides: a, b ← b, a mod b mientras b ≠ 0.
 * cocientes: "ninguna" (sin la clave), "operator.add" (se acumulan) o "sin reducer" (se reemplazan).
 */
function grafoEuclides({ entrada = "while", cocientes = "ninguna" } = {}) {
  const claves = { a: { tipo: "int" }, b: { tipo: "int" } };
  if (cocientes === "operator.add") claves.cocientes = { tipo: "list", reducer: concatenar, inicial: [] };
  if (cocientes === "sin reducer") claves.cocientes = { tipo: "list" };

  const paso = (s) => {
    const { a, b } = s;
    if (b === 0) throw new ErrorPython("ZeroDivisionError", "integer modulo by zero");
    const u = { a: b, b: a % b };
    if (cocientes !== "ninguna") u.cocientes = [Math.floor(a / b)];
    return u;
  };
  const continuar = (s) => (s.b !== 0 ? "paso" : END);
  return { claves, nodos: { paso }, aristas: aristasDeBucle(continuar, entrada) };
}

const FUNCIONES = {
  "x^2-2": { f: (x) => x ** 2 - 2, df: (x) => 2 * x, texto: "x² − 2" },
  "x^2+1": { f: (x) => x ** 2 + 1, df: (x) => 2 * x, texto: "x² + 1" },
};

/** Newton: x ← x − f(x)/f′(x) mientras |f(x)| ≥ ε. */
function grafoNewton({ funcion = "x^2-2", epsilon = 1e-10, entrada = "while" } = {}) {
  const { f, df } = FUNCIONES[funcion];
  const paso = (s) => {
    const x = s.x;
    const d = df(x);
    if (d === 0) throw new ErrorPython("ZeroDivisionError", "float division by zero");
    return { x: x - f(x) / d, n: s.n + 1 };
  };
  const continuar = (s) => (Math.abs(f(s.x)) >= epsilon ? "paso" : END);
  return { claves: { x: { tipo: "float" }, n: { tipo: "int" } }, nodos: { paso }, aristas: aristasDeBucle(continuar, entrada) };
}
return { grafoEuclides, FUNCIONES, grafoNewton };
})();

// ── motor.js
modulos["motor.js"] = (() => {
// Motor común de las simulaciones: modo claro u oscuro, canvas nítido, controles,
// botones de copiar, fórmulas con KaTeX y ayudas de dibujo. Cada simulación trae su
// propia escena y su lógica (en logica/), así que cambiar una no afecta a las demás.

const CLAVE_MODO = "complementarios-modo";

const movimientoReducido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** El modo en uso: el elegido con el botón o, si no hay, el del sistema. */
function modoActual() {
  const elegido = document.documentElement.dataset.modo;
  if (elegido === "claro" || elegido === "oscuro") return elegido;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro";
}

const avisos = new Set();

/** Llama a `fn` cada vez que cambia el modo, para redibujar el canvas con los colores nuevos. */
function alCambiarModo(fn) {
  avisos.add(fn);
}

function avisarModo() {
  for (const fn of avisos) fn();
}

/** Los colores de estilo.css, leídos en el modo actual. */
function colores() {
  const css = getComputedStyle(document.documentElement);
  const nombres = [
    "fondo", "fondo-2", "tarjeta", "borde", "borde-2", "tinta", "suave", "tenue", "nodo", "linea",
    "turquesa", "turquesa-suave", "violeta", "violeta-suave", "ambar", "ambar-suave",
    "rosa", "rosa-suave", "celeste", "celeste-suave", "verde", "verde-suave",
  ];
  const c = {};
  for (const n of nombres) c[n.replace(/-(\w)/g, (_, l) => l.toUpperCase())] = css.getPropertyValue(`--${n}`).trim();
  return c;
}

const FUENTES = {
  mono: '"IBM Plex Mono", ui-monospace, monospace',
  sans: '"IBM Plex Sans", system-ui, sans-serif',
  serif: '"Fraunces", Georgia, serif',
};

function iniciarModo() {
  const boton = document.querySelector(".modo");
  const rotular = () => {
    if (boton) boton.textContent = modoActual() === "oscuro" ? "Modo claro" : "Modo oscuro";
  };
  rotular();
  boton?.addEventListener("click", () => {
    const nuevo = modoActual() === "oscuro" ? "claro" : "oscuro";
    document.documentElement.dataset.modo = nuevo;
    try {
      localStorage.setItem(CLAVE_MODO, nuevo);
    } catch {
      /* sin almacenamiento, el modo dura hasta recargar */
    }
    rotular();
    avisarModo();
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    rotular();
    avisarModo();
  });
}

/** Los bloques aparecen al entrar en pantalla. Sin JS o con movimiento reducido, se ven de inmediato. */
function iniciarBloques() {
  const bloques = document.querySelectorAll(".blk");
  if (movimientoReducido() || !("IntersectionObserver" in window)) {
    bloques.forEach((b) => b.classList.add("in"));
    return;
  }
  const obs = new IntersectionObserver(
    (entradas) => {
      for (const e of entradas) {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          obs.unobserve(e.target);
        }
      }
    },
    { rootMargin: "0px 0px -8% 0px" },
  );
  bloques.forEach((b) => obs.observe(b));
}

/** Cada bloque de código tiene su botón, en la línea que dice el lenguaje y el archivo. */
function iniciarCopiar() {
  for (const boton of document.querySelectorAll(".lang .copy")) {
    const rotulo = boton.closest(".lang");
    boton.setAttribute("aria-label", `Copiar: ${rotulo.querySelector("span")?.textContent ?? "código"}`);
    boton.addEventListener("click", async () => {
      const codigo = rotulo.nextElementSibling.querySelector("code").textContent;
      try {
        await navigator.clipboard.writeText(codigo);
        boton.textContent = "Copiado";
        boton.classList.add("done");
        setTimeout(() => {
          boton.textContent = "Copiar";
          boton.classList.remove("done");
        }, 1600);
      } catch {
        boton.textContent = "No se pudo";
      }
    });
  }
}

/** Las fórmulas van en elementos con clase `tex` (en línea) o `tex-d` (aparte). */
function iniciarFormulas() {
  const dibujar = () => {
    if (!window.katex) return false;
    for (const el of document.querySelectorAll(".tex, .tex-d")) {
      window.katex.render(el.textContent, el, { displayMode: el.classList.contains("tex-d"), throwOnError: false });
    }
    return true;
  };
  if (!dibujar()) window.addEventListener("load", dibujar, { once: true });
}

/** Arranca lo común de la página. Llamarlo una vez, desde el módulo de la simulación. */
function iniciarPagina() {
  document.documentElement.classList.add("js");
  iniciarModo();
  iniciarBloques();
  iniciarCopiar();
  iniciarFormulas();
}

/**
 * Prepara un canvas nítido en pantallas de alta densidad. `alto(ancho)` da el alto en px CSS
 * para el ancho disponible; `dibujar(ctx, ancho, alto)` pinta la escena. Devuelve `redibujar`.
 */
function lienzo(canvas, { alto, dibujar }) {
  const ctx = canvas.getContext("2d");
  let ancho = 0;
  let h = 0;
  const medir = () => {
    ancho = canvas.parentElement.clientWidth;
    h = Math.round(alto(ancho));
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    canvas.width = Math.round(ancho * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.height = `${h}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  const redibujar = () => {
    if (!ancho) medir();
    ctx.clearRect(0, 0, ancho, h);
    dibujar(ctx, ancho, h);
  };
  new ResizeObserver(() => {
    medir();
    redibujar();
  }).observe(canvas.parentElement);
  alCambiarModo(redibujar);
  document.fonts?.ready.then(redibujar);
  return { redibujar, ancho: () => ancho };
}

/** Un grupo de botones donde se elige una opción. `opciones` = [[valor, rótulo], …]. */
function segmentado(contenedor, opciones, valor, alCambiar) {
  contenedor.replaceChildren();
  const botones = opciones.map(([v, rotulo]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = rotulo;
    b.setAttribute("aria-pressed", String(v === valor));
    b.addEventListener("click", () => {
      botones.forEach((o) => o.setAttribute("aria-pressed", String(o === b)));
      alCambiar(v);
    });
    contenedor.append(b);
    return b;
  });
}

/** Un deslizador con su valor a la vista. `formato(v)` da el texto del valor. */
function deslizador(input, salida, formato, alCambiar) {
  const mostrar = () => {
    salida.textContent = formato(Number(input.value));
  };
  input.addEventListener("input", () => {
    mostrar();
    alCambiar(Number(input.value));
  });
  mostrar();
}

// ── Ayudas de dibujo ────────────────────────────────────────────────────────

function cajaRedonda(ctx, x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(x, y, w, h, r);
    return;
  }
  // Safari anterior a 16 no tiene roundRect.
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** Punto y tangente de la curva cuadrática p0 → p2 con control p1, en t ∈ [0, 1]. */
function enCurva(p0, p1, p2, t) {
  const u = 1 - t;
  return {
    x: u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x,
    y: u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y,
    dx: 2 * u * (p1.x - p0.x) + 2 * t * (p2.x - p1.x),
    dy: 2 * u * (p1.y - p0.y) + 2 * t * (p2.y - p1.y),
  };
}

/** Flecha curva de p0 a p2 con control p1. */
function flecha(ctx, p0, p1, p2, { color, ancho = 1.5, punteada = false, punta = 7 }) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = ancho;
  ctx.setLineDash(punteada ? [5, 5] : []);
  ctx.beginPath();
  ctx.moveTo(p0.x, p0.y);
  ctx.quadraticCurveTo(p1.x, p1.y, p2.x, p2.y);
  ctx.stroke();
  ctx.setLineDash([]);
  const { dx, dy } = enCurva(p0, p1, p2, 1);
  const ang = Math.atan2(dy, dx);
  ctx.beginPath();
  ctx.moveTo(p2.x, p2.y);
  ctx.lineTo(p2.x - punta * Math.cos(ang - 0.42), p2.y - punta * Math.sin(ang - 0.42));
  ctx.lineTo(p2.x - punta * Math.cos(ang + 0.42), p2.y - punta * Math.sin(ang + 0.42));
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

/** Texto con fondo, para rotular una arista sin que la línea lo tape. */
function rotulo(ctx, texto, x, y, { color, fondo, fuente, alinear = "center" }) {
  ctx.save();
  ctx.font = fuente;
  const w = ctx.measureText(texto).width;
  const h = parseFloat(fuente) * 1.35;
  const x0 = alinear === "center" ? x - w / 2 : alinear === "right" ? x - w : x;
  ctx.fillStyle = fondo;
  ctx.fillRect(x0 - 4, y - h / 2, w + 8, h);
  ctx.fillStyle = color;
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  ctx.fillText(texto, x0, y + 0.5);
  ctx.restore();
}

/** Reloj de animación: llama a `cuadro(t)` con t de 0 a 1 durante `ms`, y después a `fin`. */
function animar(ms, cuadro, fin) {
  if (movimientoReducido()) {
    cuadro(1);
    fin?.();
    return () => {};
  }
  let vivo = true;
  const t0 = performance.now();
  const tick = (ahora) => {
    if (!vivo) return;
    const t = Math.min(1, (ahora - t0) / ms);
    cuadro(t);
    if (t < 1) requestAnimationFrame(tick);
    else fin?.();
  };
  requestAnimationFrame(tick);
  return () => {
    vivo = false;
  };
}

const suavizar = (t) => 1 - Math.pow(1 - t, 3);
return { movimientoReducido, modoActual, alCambiarModo, colores, FUENTES, iniciarPagina, lienzo, segmentado, deslizador, cajaRedonda, enCurva, flecha, rotulo, animar, suavizar };
})();

// ── escenas/supersteps.js
modulos["escenas/supersteps.js"] = (() => {
const { END, START, ejecutar } = modulos["logica/grafo.js"];
const { repr, reprDict } = modulos["logica/repr.js"];
const { FUNCIONES, grafoEuclides, grafoNewton } = modulos["logica/supersteps.js"];
const { FUENTES, animar, cajaRedonda, colores, deslizador, enCurva, flecha, iniciarPagina, lienzo, movimientoReducido, rotulo, segmentado, suavizar } = modulos["motor.js"];
// Escena de la simulación 1: el grafo START → paso → END, corriendo un superstep a la vez.






iniciarPagina();

const $ = (sel) => document.querySelector(sel);

// ── Estado de los controles ──────────────────────────────────────────────────

const opciones = {
  algoritmo: "euclides",
  entrada: "while",
  cocientes: "operator.add",
  a: 1071,
  b: 462,
  funcion: "x^2-2",
  x0: 1,
  epsilon: 1e-10,
  limite: 25,
};

// ── La ejecución y sus fotogramas ────────────────────────────────────────────
// Un fotograma por superstep, más uno final: END alcanzado o el error.

let grafo;
let corrida;
let fotogramas = [];
let actual = 0;
let progreso = 1; // 0 → 1 mientras se anima la llegada al fotograma actual
let detener = () => {};
let reproduciendo = false;
let reloj = null;

function correr() {
  grafo =
    opciones.algoritmo === "euclides"
      ? grafoEuclides({ entrada: opciones.entrada, cocientes: opciones.cocientes })
      : grafoNewton({ funcion: opciones.funcion, epsilon: opciones.epsilon, entrada: opciones.entrada });
  const entrada =
    opciones.algoritmo === "euclides"
      ? { a: opciones.a, b: opciones.b, ...(opciones.cocientes === "ninguna" ? {} : { cocientes: [] }) }
      : { x: opciones.x0, n: 0 };
  corrida = ejecutar(grafo, entrada, { limite: opciones.limite });
  fotogramas = corrida.pasos.map((p) => ({ tipo: "paso", paso: p }));
  const ultimo = corrida.pasos[corrida.pasos.length - 1];
  if (corrida.error) fotogramas.push({ tipo: "error", error: corrida.error, previo: ultimo });
  else fotogramas.push({ tipo: "fin", previo: ultimo });
}

// ── Dibujo ───────────────────────────────────────────────────────────────────

const canvas = $("#stage");
const indice = $("#idx");

function disposicion(ancho) {
  const angosto = ancho < 560;
  const altoGrafo = angosto ? 190 : 200;
  // Una línea por clave, y al menos tres: las tarjetas de END y de GraphRecursionError usan tres.
  const nLineas = Math.max(3, Object.keys(grafo.claves).length);
  const altoTarjeta = 46 + nLineas * 22;
  const altoTarjetas = angosto ? altoTarjeta * 2 + 12 : altoTarjeta;
  return { angosto, altoGrafo, altoTarjeta, alto: altoGrafo + altoTarjetas + 30 };
}

const vista = lienzo(canvas, {
  alto: (ancho) => disposicion(ancho).alto,
  dibujar: (ctx, ancho, alto) => dibujar(ctx, ancho, alto),
});

function posiciones(ancho, d) {
  // En el teléfono el grafo baja un poco, para que el bucle no choque con el rótulo de la esquina.
  const y = d.altoGrafo * (d.angosto ? 0.6 : 0.56);
  const margen = d.angosto ? 8 : 34;
  const wIni = d.angosto ? 62 : 92;
  const wFin = d.angosto ? 54 : 80;
  const wPaso = d.angosto ? 78 : 120;
  return {
    [START]: { x: margen + wIni / 2, y, w: wIni, h: 36, ovalo: true, texto: "START" },
    paso: { x: ancho / 2, y, w: wPaso, h: 46, ovalo: false, texto: "paso" },
    [END]: { x: ancho - margen - wFin / 2, y, w: wFin, h: 36, ovalo: true, texto: "END" },
  };
}

/** Las aristas del grafo como curvas: { origen, destino, p0, p1, p2, condicional, rotulo }. */
function aristas(P, angosto) {
  const borde = (n, lado) => ({ x: P[n].x + (lado * P[n].w) / 2, y: P[n].y });
  const condiciones = opciones.algoritmo === "euclides" ? ["b ≠ 0", "b = 0"] : ["|f(x)| ≥ ε", "|f(x)| < ε"];
  // En el teléfono, sin espacios: así el rótulo cabe entre START y paso.
  const [sigue, para] = angosto ? condiciones.map((c) => c.replaceAll(" ", "")) : condiciones;
  const lista = [];
  const condicionalInicio = opciones.entrada === "while";
  {
    const p0 = borde(START, 1);
    const p2 = borde("paso", -1);
    lista.push({ origen: START, destino: "paso", p0, p1: { x: (p0.x + p2.x) / 2, y: p0.y }, p2, condicional: condicionalInicio, rotulo: condicionalInicio ? sigue : "" });
  }
  if (condicionalInicio) {
    const p0 = { x: P[START].x, y: P[START].y + P[START].h / 2 };
    const p2 = { x: P[END].x, y: P[END].y + P[END].h / 2 };
    lista.push({ origen: START, destino: END, p0, p1: { x: (p0.x + p2.x) / 2, y: p0.y + 74 }, p2, condicional: true, rotulo: para });
  }
  {
    const p0 = borde("paso", 1);
    const p2 = borde(END, -1);
    lista.push({ origen: "paso", destino: END, p0, p1: { x: (p0.x + p2.x) / 2, y: p0.y }, p2, condicional: true, rotulo: para });
  }
  {
    const n = P.paso;
    const p0 = { x: n.x + n.w * 0.22, y: n.y - n.h / 2 };
    const p2 = { x: n.x - n.w * 0.22, y: n.y - n.h / 2 };
    lista.push({ origen: "paso", destino: "paso", p0, p1: { x: n.x, y: n.y - n.h / 2 - 92 }, p2, condicional: true, rotulo: sigue, bucle: true });
  }
  return lista;
}

function aristaDe(lista, origen, destino) {
  return lista.find((a) => a.origen === origen && a.destino === destino);
}

/** Qué se ve en el fotograma: nodo encendido, arista recorrida y si hay error. */
function escena() {
  const f = fotogramas[actual];
  if (f.tipo === "paso") {
    const p = f.paso;
    const nodo = p.nodos[0];
    const previo = actual > 0 ? fotogramas[actual - 1].paso : null;
    const origen = previo ? previo.nodos[0] : null;
    return { nodo, recorrida: origen ? [origen, nodo] : null, paso: p, error: null };
  }
  if (f.tipo === "fin") {
    return { nodo: END, recorrida: [f.previo.nodos[0], END], paso: f.previo, error: null };
  }
  const e = f.error;
  if (e.tipo === "GraphRecursionError") {
    return { nodo: null, recorrida: null, paso: f.previo, error: e };
  }
  // Un nodo falló: la arista llega, el nodo se enciende en rosa y no hay estado nuevo.
  return { nodo: e.nodos[0], recorrida: [f.previo.nodos[0], e.nodos[0]], paso: f.previo, error: e, fallo: true };
}

function dibujar(ctx, ancho, alto) {
  if (!grafo) return;
  const c = colores();
  const d = disposicion(ancho);
  const P = posiciones(ancho, d);
  const lista = aristas(P, d.angosto);
  const e = escena();
  const t = suavizar(progreso);
  const llego = progreso >= 0.55;

  ctx.fillStyle = c.fondo2;
  ctx.fillRect(0, 0, ancho, alto);

  // Aristas
  const fuenteRotulo = `${d.angosto ? 10 : 11}px ${FUENTES.mono}`;
  for (const a of lista) {
    const activa = e.recorrida && a.origen === e.recorrida[0] && a.destino === e.recorrida[1];
    const color = activa ? (e.fallo ? c.rosa : c.turquesa) : c.linea;
    flecha(ctx, a.p0, a.p1, a.p2, { color, ancho: activa ? 2.2 : 1.4, punteada: a.condicional });
    if (a.rotulo) {
      const m = enCurva(a.p0, a.p1, a.p2, 0.5);
      const dy = a.bucle ? -2 : a.destino === END && a.origen === START ? 0 : -13;
      rotulo(ctx, a.rotulo, m.x, m.y + dy, { color: activa ? c.tinta : c.suave, fondo: c.fondo2, fuente: fuenteRotulo });
    }
  }

  // Nodos
  for (const [nombre, n] of Object.entries(P)) {
    const encendido = e.nodo === nombre && llego;
    const fallo = encendido && e.fallo;
    ctx.save();
    ctx.lineWidth = encendido ? 2.6 : 1.6;
    ctx.strokeStyle = fallo ? c.rosa : encendido ? c.turquesa : c.borde2;
    ctx.fillStyle = fallo ? c.rosaSuave : encendido ? c.turquesaSuave : n.ovalo ? c.tarjeta : c.nodo;
    if (n.ovalo) {
      ctx.beginPath();
      ctx.ellipse(n.x, n.y, n.w / 2, n.h / 2, 0, 0, Math.PI * 2);
    } else {
      cajaRedonda(ctx, n.x - n.w / 2, n.y - n.h / 2, n.w, n.h, 10);
    }
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = n.ovalo && !encendido ? c.suave : c.tinta;
    ctx.font = `${n.ovalo ? 500 : 600} ${n.ovalo ? (d.angosto ? 11 : 12) : d.angosto ? 14 : 15}px ${FUENTES.mono}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(n.texto, n.x, n.y + 1);
    ctx.restore();
  }

  // La ficha que recorre la arista
  if (e.recorrida && progreso < 1) {
    const a = aristaDe(lista, e.recorrida[0], e.recorrida[1]);
    if (a) {
      const q = enCurva(a.p0, a.p1, a.p2, Math.min(1, t / 0.55));
      ctx.save();
      ctx.fillStyle = e.fallo ? c.rosa : c.turquesa;
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 12;
      ctx.beginPath();
      ctx.arc(q.x, q.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  dibujarTarjetas(ctx, ancho, d, c, e, llego);
}

function dibujarTarjetas(ctx, ancho, d, c, e, llego) {
  const margen = d.angosto ? 12 : 24;
  const y0 = d.altoGrafo + 6;
  const w = d.angosto ? ancho - 2 * margen : (ancho - 2 * margen - 16) / 2;
  const cajas = d.angosto
    ? [{ x: margen, y: y0 }, { x: margen, y: y0 + d.altoTarjeta + 12 }]
    : [{ x: margen, y: y0 }, { x: margen + w + 16, y: y0 }];

  const p = e.paso;
  const claves = grafo.claves;
  const k = p.k;
  const sub = (n) => String(n).replace(/\d/g, (x) => "₀₁₂₃₄₅₆₇₈₉"[x]);

  // Tarjeta 1: la actualización (o la entrada, en el superstep 0)
  let titulo1;
  let lineas1;
  if (e.error && e.fallo) {
    titulo1 = `${e.error.tipo}`;
    lineas1 = [[e.error.mensaje, c.rosa], [`en paso, superstep ${e.error.k}`, c.suave]];
  } else if (e.error) {
    titulo1 = "GraphRecursionError";
    lineas1 = [[`recursion_limit = ${opciones.limite}`, c.rosa], [`se usaron ${k + 1} supersteps,`, c.suave], ["contando el de START", c.suave]];
  } else if (e.nodo === END && llego) {
    titulo1 = "END";
    lineas1 = [["c(s) eligió END:", c.suave], ["no queda ningún nodo", c.suave], [`invoke devuelve s${sub(k)}`, c.tinta]];
  } else if (k === 0) {
    titulo1 = "entrada e";
    lineas1 = Object.entries(p.actualizaciones[0]).map(([clave, v]) => [`${clave}: ${repr(v, claves[clave]?.tipo)}`, c.tinta]);
  } else {
    titulo1 = `u = φ(s${sub(k - 1)})`;
    lineas1 = Object.entries(p.actualizaciones[0]).map(([clave, v]) => [`${clave}: ${repr(v, claves[clave]?.tipo)}`, c.tinta]);
  }

  // Tarjeta 2: el estado que resulta, clave por clave, con el reducer a la vista
  const titulo2 = k === 0 ? "s₀ = s∅ ⊕ e" : `s${sub(k)} = s${sub(k - 1)} ⊕ u`;
  // Después del último estado (END o un error) no hay escritura nueva que resaltar.
  const resaltar = k > 0 && llego && !e.error && e.nodo !== END;
  const lineas2 = Object.keys(claves).map((clave) => {
    const v = p.estado[clave];
    const antes = p.antes ? p.antes[clave] : undefined;
    const u = p.actualizaciones[0];
    const escrita = clave in u;
    const tipo = claves[clave].tipo;
    let texto = `${clave}: ${repr(v, tipo)}`;
    if (escrita && claves[clave].reducer && antes !== undefined) {
      texto = `${clave}: ${repr(antes, tipo)} + ${repr(u[clave], tipo)} = ${repr(v, tipo)}`;
    } else if (escrita && k > 0 && Array.isArray(v)) {
      texto = `${clave}: ${repr(v, tipo)}  (reemplaza)`;
    }
    return [texto, escrita && resaltar ? c.turquesa : c.tinta];
  });

  const fuente = `${d.angosto ? 11.5 : 12.5}px ${FUENTES.mono}`;
  const tarjeta = (caja, titulo, lineas, marco) => {
    ctx.save();
    cajaRedonda(ctx, caja.x, caja.y, w, d.altoTarjeta, 10);
    ctx.fillStyle = c.fondo;
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = marco;
    ctx.stroke();
    ctx.fillStyle = marco === c.borde ? c.suave : marco;
    ctx.font = `600 ${d.angosto ? 10.5 : 11}px ${FUENTES.mono}`;
    ctx.textBaseline = "top";
    ctx.fillText(titulo, caja.x + 12, caja.y + 12);
    ctx.font = fuente;
    lineas.forEach(([texto, color], i) => {
      ctx.fillStyle = color;
      ctx.fillText(recortar(ctx, texto, w - 24), caja.x + 12, caja.y + 36 + i * 22);
    });
    ctx.restore();
  };
  const marco1 = e.error ? c.rosa : c.borde;
  tarjeta(cajas[0], titulo1, llego || k === 0 ? lineas1 : [], marco1);
  tarjeta(cajas[1], titulo2, lineas2, c.borde);
}

function recortar(ctx, texto, max) {
  if (ctx.measureText(texto).width <= max) return texto;
  let t = texto;
  while (t.length > 4 && ctx.measureText(`${t}…`).width > max) t = t.slice(0, -1);
  return `${t}…`;
}

// ── La traza: stream(stream_mode="values") ───────────────────────────────────

const cuerpoTraza = $("#traza tbody");
const resumenTraza = $("#traza-resumen");

function pintarTraza() {
  const filas = fotogramas.map((f, i) => {
    const tr = document.createElement("tr");
    const celda = (texto, clase) => {
      const td = document.createElement("td");
      td.textContent = texto;
      if (clase) td.className = clase;
      tr.append(td);
    };
    if (f.tipo === "paso") {
      const p = f.paso;
      celda(String(p.k), "k");
      celda(p.k === 0 ? "START" : p.nodos.join(", "));
      celda(reprDict(p.estado, grafo.claves));
    } else if (f.tipo === "fin") {
      celda("", "k");
      celda("END");
      celda("termina");
    } else {
      celda("", "k");
      celda(f.error.tipo);
      celda(f.error.tipo === "GraphRecursionError" ? `recursion_limit = ${opciones.limite}` : f.error.mensaje);
      tr.classList.add("error");
    }
    tr.tabIndex = 0;
    tr.addEventListener("click", () => {
      pausar();
      irA(i, false);
    });
    tr.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        pausar();
        irA(i, false);
      }
    });
    return tr;
  });
  cuerpoTraza.replaceChildren(...filas);
  const n = corrida.pasos.length;
  resumenTraza.textContent = `${n} ${n === 1 ? "estado" : "estados"}${corrida.error ? ` · ${corrida.error.tipo}` : ""}`;
  marcarTraza();
}

function marcarTraza() {
  [...cuerpoTraza.children].forEach((tr, i) => {
    tr.classList.toggle("actual", i === actual && !tr.classList.contains("error"));
    tr.classList.toggle("pendiente", i > actual);
    if (i === actual) tr.setAttribute("aria-current", "step");
    else tr.removeAttribute("aria-current");
  });
  const fila = cuerpoTraza.children[actual];
  if (fila) {
    const caja = fila.parentElement.closest(".traza-cuerpo");
    const arriba = fila.offsetTop - caja.clientHeight / 2;
    caja.scrollTo({ top: Math.max(0, arriba), behavior: movimientoReducido() ? "auto" : "smooth" });
  }
}

// ── Navegación ───────────────────────────────────────────────────────────────

const botones = {
  atras: $("#atras"),
  paso: $("#paso"),
  reproducir: $("#reproducir"),
  reiniciar: $("#reiniciar"),
};

function actualizarIndice() {
  const f = fotogramas[actual];
  indice.textContent = f.tipo === "paso" ? `superstep ${f.paso.k}` : f.tipo === "fin" ? "END" : f.error.tipo;
  botones.atras.disabled = actual === 0;
  botones.paso.disabled = actual === fotogramas.length - 1;
  botones.reproducir.textContent = reproduciendo ? "❚❚ Pausa" : actual === fotogramas.length - 1 ? "↻ Otra vez" : "▶ Reproducir";
}

function irA(i, animado = true) {
  detener();
  actual = Math.max(0, Math.min(fotogramas.length - 1, i));
  marcarTraza();
  actualizarIndice();
  if (animado && !movimientoReducido()) {
    progreso = 0;
    detener = animar(
      900,
      (t) => {
        progreso = t;
        vista.redibujar();
      },
      () => {
        progreso = 1;
        vista.redibujar();
      },
    );
  } else {
    progreso = 1;
    vista.redibujar();
  }
}

function pausar() {
  reproduciendo = false;
  clearTimeout(reloj);
  actualizarIndice();
}

function reproducir() {
  if (reproduciendo) return; // una sola cadena de temporizadores a la vez
  if (actual === fotogramas.length - 1) irA(0, false);
  reproduciendo = true;
  actualizarIndice();
  const siguiente = () => {
    if (!reproduciendo) return;
    if (actual >= fotogramas.length - 1) {
      pausar();
      return;
    }
    irA(actual + 1);
    if (actual >= fotogramas.length - 1) {
      pausar();
      return;
    }
    reloj = setTimeout(siguiente, movimientoReducido() ? 900 : 1500);
  };
  reloj = setTimeout(siguiente, 500);
}

botones.atras.addEventListener("click", () => {
  pausar();
  irA(actual - 1, false);
});
botones.paso.addEventListener("click", () => {
  pausar();
  irA(actual + 1);
});
botones.reproducir.addEventListener("click", () => (reproduciendo ? pausar() : reproducir()));
botones.reiniciar.addEventListener("click", () => {
  pausar();
  irA(0, false);
});

// ── Controles ────────────────────────────────────────────────────────────────

function rehacer({ reproducirAlFinal = true } = {}) {
  pausar();
  correr();
  actual = 0;
  pintarTraza();
  vista.redibujar();
  irA(0, false);
  mostrarControles();
  if (reproducirAlFinal && !movimientoReducido()) reproducir();
}

function mostrarControles() {
  const euclides = opciones.algoritmo === "euclides";
  document.querySelectorAll("[data-solo]").forEach((el) => {
    el.hidden = el.dataset.solo !== opciones.algoritmo;
  });
  $("#titulo-estado").textContent = euclides ? "EstadoMCD" : "EstadoNewton";
}

segmentado($("#ctl-algoritmo"), [["euclides", "Euclides"], ["newton", "Newton"]], opciones.algoritmo, (v) => {
  opciones.algoritmo = v;
  rehacer();
});
segmentado($("#ctl-entrada"), [["while", "while · condicional"], ["do-while", "do-while · fija"]], opciones.entrada, (v) => {
  opciones.entrada = v;
  rehacer();
});
segmentado(
  $("#ctl-cocientes"),
  [["ninguna", "sin la clave"], ["operator.add", "operator.add"], ["sin reducer", "sin reducer"]],
  opciones.cocientes,
  (v) => {
    opciones.cocientes = v;
    rehacer();
  },
);
segmentado(
  $("#ctl-funcion"),
  Object.entries(FUNCIONES).map(([k, f]) => [k, f.texto]),
  opciones.funcion,
  (v) => {
    opciones.funcion = v;
    rehacer();
  },
);
segmentado($("#ctl-epsilon"), [[1e-10, "10⁻¹⁰"], [1e-4, "10⁻⁴"]], opciones.epsilon, (v) => {
  opciones.epsilon = v;
  rehacer();
});

for (const clave of ["a", "b"]) {
  const input = $(`#ctl-${clave}`);
  input.value = opciones[clave];
  input.addEventListener("change", () => {
    const v = Math.max(0, Math.min(100000, Math.floor(Number(input.value) || 0)));
    input.value = v;
    opciones[clave] = v;
    // Sin reproducir: el cambio llega al salir del campo, a veces con el mismo toque que va a Reproducir.
    rehacer({ reproducirAlFinal: false });
  });
}
document.querySelectorAll("[data-ab]").forEach((b) => {
  b.addEventListener("click", () => {
    const [a, bb] = b.dataset.ab.split(",").map(Number);
    opciones.a = a;
    opciones.b = bb;
    $("#ctl-a").value = a;
    $("#ctl-b").value = bb;
    rehacer();
  });
});

deslizador($("#ctl-x0"), $("#val-x0"), (v) => v.toFixed(2), (v) => {
  opciones.x0 = v;
  rehacer({ reproducirAlFinal: false });
});
deslizador($("#ctl-limite"), $("#val-limite"), (v) => String(v), (v) => {
  opciones.limite = v;
  rehacer({ reproducirAlFinal: false });
});

// ── Arranque ─────────────────────────────────────────────────────────────────

correr();
pintarTraza();
mostrarControles();
irA(0, false);

// Reproduce sola la primera vez que el escenario entra en pantalla.
const primera = new IntersectionObserver((entradas) => {
  if (entradas.some((e) => e.isIntersecting)) {
    primera.disconnect();
    // Solo si nadie avanzó ni está reproduciendo ya.
    if (!movimientoReducido() && !reproduciendo && actual === 0) reproducir();
  }
});
primera.observe(canvas);
return {  };
})();
})();
