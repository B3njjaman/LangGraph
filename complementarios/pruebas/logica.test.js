// Compara la lógica en JS de las simulaciones con los casos que generó LangGraph real.
// Uso, desde la raíz:  node --test "complementarios/pruebas/*.test.js"
// Para regenerar los casos:  python complementarios/pruebas/generar_casos.py

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { ejecutar } from "../logica/grafo.js";
import { grafoEuclides, grafoNewton } from "../logica/supersteps.js";

const leer = (nombre) => JSON.parse(readFileSync(new URL(`./casos/${nombre}`, import.meta.url), "utf-8"));

test("supersteps: Euclides y Newton dan los mismos estados y errores que LangGraph", () => {
  const { casos } = leer("supersteps.json");
  assert.ok(casos.length > 400);
  for (const c of casos) {
    const grafo =
      c.algoritmo === "euclides"
        ? grafoEuclides({ entrada: c.entrada, cocientes: c.cocientes })
        : grafoNewton({ funcion: c.funcion, epsilon: c.epsilon, entrada: c.entrada });
    const entrada =
      c.algoritmo === "euclides"
        ? { a: c.a, b: c.b, ...(c.cocientes === "ninguna" ? {} : { cocientes: [] }) }
        : { x: c.x0, n: 0 };
    const { pasos, error } = ejecutar(grafo, entrada, { limite: c.limite });
    const nombre = JSON.stringify({ ...c, estados: undefined, error: undefined });
    assert.deepEqual(pasos.map((p) => p.estado), c.estados, nombre);
    assert.equal(error?.tipo ?? null, c.error?.tipo ?? null, nombre);
    if (c.error?.mensaje) assert.equal(error.mensaje, c.error.mensaje, nombre);
  }
});
