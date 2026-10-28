// Valores escritos como los escribe Python, para que la traza se lea igual que en el notebook.

/** repr de un float de Python: 1.0 y no 1; 1e-07 y no 1e-7. */
export function reprFloat(x) {
  if (Number.isNaN(x)) return "nan";
  if (!Number.isFinite(x)) return x > 0 ? "inf" : "-inf";
  if (Number.isInteger(x) && Math.abs(x) < 1e16) return x.toFixed(1);
  return String(x).replace(/e([+-])(\d)$/, "e$10$2");
}

/** repr de un valor según el tipo de su clave ("int", "float" o "list"). */
export function repr(valor, tipo) {
  if (Array.isArray(valor)) return `[${valor.map((v) => repr(v, "int")).join(", ")}]`;
  if (tipo === "float") return reprFloat(valor);
  return String(valor);
}

/** repr de un estado: {'a': 21, 'b': 0}, con las claves en el orden del esquema, como Python. */
export function reprDict(d, claves) {
  const orden = Object.keys(claves).filter((k) => k in d);
  const partes = orden.map((k) => `'${k}': ${repr(d[k], claves[k].tipo)}`);
  return `{${partes.join(", ")}}`;
}
