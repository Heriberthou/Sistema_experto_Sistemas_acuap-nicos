/** Funciones de presentación compartidas. Aquí no se realiza inferencia. */

/** Escapa contenido antes de incorporarlo a una plantilla HTML. */
export function escapar(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, caracter => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[caracter]));
}

/** Envía una petición local y convierte los errores HTTP en mensajes legibles. */
export async function solicitar(ruta, contenido) {
  const respuesta = await fetch(ruta, contenido === undefined ? {} : {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(contenido)
  });
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new Error(datos.error || "No fue posible completar la consulta.");
  return datos;
}

/** Traduce los estados internos V/F/D. */
export function formatearValor(valor) {
  return {V:"Sí", F:"No", D:"Desconozco"}[valor] || String(valor);
}

const TRAZOS = {
  agua:'<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z"/><path d="M9.5 14.5a2.5 2.5 0 0 0 2.5 2.5"/>',
  peces:'<path d="M3 12c3-5 8-6 12-3l6-3v12l-6-3c-4 3-9 2-12-3Z"/><circle cx="8.5" cy="11" r=".8" fill="currentColor"/>',
  equipos:'<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>',
  plantas:'<path d="M5 19c0-8 5-14 15-14 0 9-5 15-13 15"/><path d="M5 19c3-5 6-8 10-10"/>',
  contexto:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  alerta:'<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4M12 17.5v.1"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.1"/>',
  ok:'<circle cx="12" cy="12" r="9"/><path d="m8 12.5 3 3 5-6"/>',
  sol:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/>',
  luna:'<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/>',
  flecha:'<path d="M5 12h14M13 6l6 6-6 6"/>',
  atras:'<path d="M19 12H5M11 6l-6 6 6 6"/>',
  imprimir:'<path d="M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z"/>',
  descargar:'<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>',
  reiniciar:'<path d="M4 12a8 8 0 1 1 3 6.2M4 19v-5h5"/>',
  lista:'<path d="M8 6h12M8 12h12M8 18h12M4 6h.1M4 12h.1M4 18h.1"/>',
};

/** Icono de trazo; hereda el color del texto. */
export function icono(nombre) {
  return `<svg class="icono" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${TRAZOS[nombre] || ""}</svg>`;
}

export const GRUPOS = {
  agua:{nombre:"Calidad del agua", icono:"agua"}, peces:{nombre:"Tus peces", icono:"peces"},
  equipos:{nombre:"Bomba y aireación", icono:"equipos"}, plantas:{nombre:"Tus lechugas", icono:"plantas"},
  contexto:{nombre:"Etapa del sistema", icono:"contexto"},
};

export const SUSTENTO = {
  Medida:"Sale de una medición que respondiste.", Observada:"Sale de algo que observaste.",
  Hipótesis:"Es una inferencia del sistema, no un diagnóstico.",
};

/** Urgencia según la prioridad del documento (1 es la más urgente). */
export function urgencia(prioridad) {
  if (prioridad <= 5) return {clase:"u1", texto:"Urgente"};
  if (prioridad <= 12) return {clase:"u2", texto:"Prioritario"};
  return {clase:"u3", texto:"Puedes programarlo"};
}

/** Quita del texto de una acción el título repetido al inicio. */
export function sinTitulo(elemento) {
  const prefijo = `${elemento.titulo}:`;
  const texto = elemento.descripcion.startsWith(prefijo) ? elemento.descripcion.slice(prefijo.length).trim() : elemento.descripcion;
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Presenta la evidencia visitada de cada regla y su referencia documental. */
export function pintarTraza(pasos) {
  if (!pasos.length) return '<p class="texto-secundario">Ninguna regla se activó.</p>';
  return pasos.map((paso, indice) => `<article class="traza-paso"><strong>Paso ${indice+1} · ${escapar(paso.regla)} → ${escapar(paso.conclusion)}</strong><p><code>${escapar(paso.expresion)}</code></p><ul>${paso.evidencias.map(evidencia => `<li>${escapar(evidencia.hecho)} = ${escapar(evidencia.valor)} (se esperaba ${escapar(evidencia.referencia)}): ${escapar(evidencia.estado)}</li>`).join("")}</ul><p>${escapar(paso.explicacion)}</p><p class="texto-secundario">${paso.fuentes.map(f => `<span class="chip">${escapar(f)}</span>`).join("")}${escapar(paso.cita)}${paso.inferencia ? ' <span class="chip inferencia">inferencia propuesta</span>' : ""}</p></article>`).join("");
}

/** Descarga un informe únicamente cuando la persona pulsa el botón. */
export function descargarInforme(contenido) {
  const direccion = URL.createObjectURL(new Blob([JSON.stringify(contenido, null, 2)], {type:"application/json"}));
  const enlace = document.createElement("a");
  enlace.href = direccion; enlace.download = "consulta-acuaponia.json"; enlace.click();
  setTimeout(() => URL.revokeObjectURL(direccion), 1000);
}

/** Alterna entre tema claro y oscuro; la preferencia solo se recuerda en este navegador. */
export function iniciarTema() {
  const raiz = document.documentElement;
  let guardado = null;
  try { guardado = localStorage.getItem("acuavida-tema"); } catch { guardado = null; }
  const oscuro = guardado ? guardado === "oscuro" : matchMedia("(prefers-color-scheme: dark)").matches;
  raiz.dataset.tema = oscuro ? "oscuro" : "claro";
  const boton = document.querySelector("#boton-tema");
  if (!boton) return;
  const pintar = () => { boton.innerHTML = icono(raiz.dataset.tema === "oscuro" ? "sol" : "luna"); boton.setAttribute("aria-label", raiz.dataset.tema === "oscuro" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"); };
  pintar();
  boton.addEventListener("click", () => {
    raiz.dataset.tema = raiz.dataset.tema === "oscuro" ? "claro" : "oscuro";
    try { localStorage.setItem("acuavida-tema", raiz.dataset.tema); } catch { /* sin almacenamiento disponible */ }
    pintar();
  });
}
