// Escena de la simulación 1: el grafo START → paso → END, corriendo un superstep a la vez.

import { END, START, ejecutar } from "../logica/grafo.js";
import { repr, reprDict } from "../logica/repr.js";
import { FUNCIONES, grafoEuclides, grafoNewton } from "../logica/supersteps.js";
import {
  FUENTES, animar, cajaRedonda, colores, deslizador, enCurva, flecha, iniciarPagina, lienzo,
  movimientoReducido, rotulo, segmentado, suavizar,
} from "../motor.js";

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
