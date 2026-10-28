// Los grafos de la lección 1: Euclides y Newton, con la arista de entrada como `while` o `do-while`.

import { END, ErrorPython, START } from "./grafo.js";

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
export function grafoEuclides({ entrada = "while", cocientes = "ninguna" } = {}) {
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

export const FUNCIONES = {
  "x^2-2": { f: (x) => x ** 2 - 2, df: (x) => 2 * x, texto: "x² − 2" },
  "x^2+1": { f: (x) => x ** 2 + 1, df: (x) => 2 * x, texto: "x² + 1" },
};

/** Newton: x ← x − f(x)/f′(x) mientras |f(x)| ≥ ε. */
export function grafoNewton({ funcion = "x^2-2", epsilon = 1e-10, entrada = "while" } = {}) {
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
