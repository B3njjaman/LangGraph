// Ejecución de un grafo de estado por supersteps, con la semántica de LangGraph 1.2.17.
// Es la parte de las simulaciones que no dibuja: se prueba en Node contra LangGraph real
// (complementarios/pruebas/logica.test.js).

export const START = "START";
export const END = "END";

/** Un error que en Python lanzaría el código de un nodo, con su tipo y su mensaje. */
export class ErrorPython extends Error {
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
export function aplicar(grafo, s, actualizaciones) {
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
export function ejecutar(grafo, entrada, { limite = 10007 } = {}) {
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

export function mensajeLimite(limite) {
  return `Recursion limit of ${limite} reached without hitting a stop condition.`;
}
