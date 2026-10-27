/** Laboratorio académico: demuestra y compara los dos mecanismos y ejecuta los casos del documento. */
import {escapar, solicitar, pintarTraza, GRUPOS, iniciarTema} from "/utilidades.js";
const seleccionar = selector => document.querySelector(selector);
let base, casos = [], ocupado = false;

/** Habilita o bloquea los controles durante una petición HTTP. */
function establecerCarga(valor) {
  ocupado = valor;
  document.querySelectorAll("button, select").forEach(control => { control.disabled = valor; });
}

/** Presenta los errores de validación sin convertirlos en resultados del motor. */
function mostrarError(error) {
  seleccionar("#error-laboratorio").textContent = error.message;
  seleccionar("#error-laboratorio").hidden = false;
}

/** Construye un selector Sí/No/Desconozco por pregunta, agrupado por área. */
function presentarEntradas(hechos = {}) {
  let html = "";
  for (const [grupo, datos] of Object.entries(GRUPOS)) {
    const preguntas = base.preguntas.filter(p => p.grupo === grupo);
    if (!preguntas.length) continue;
    html += `<p class="grupo-laboratorio">${escapar(datos.nombre)}</p>` + preguntas.map(p => `<label class="entrada-laboratorio"><span>${p.id}</span><small>${escapar(p.texto)}</small><select data-hecho="${p.id}">${[["D", "Desconozco"], ["V", "Sí"], ["F", "No"]].map(([valor, texto]) => `<option value="${valor}" ${(hechos[p.id] || "D") === valor ? "selected" : ""}>${texto}</option>`).join("")}</select></label>`).join("");
  }
  seleccionar("#entradas").innerHTML = html;
}

/** Lee las entradas; solo viajan las respuestas distintas de Desconozco. */
function capturarHechos() {
  return Object.fromEntries(base.preguntas.map(p => [p.id, seleccionar(`[data-hecho="${p.id}"]`).value]).filter(([, v]) => v !== "D"));
}

/** Resume un mecanismo sin confundir un fracaso de prueba con una negación real. */
function resumir(informe) {
  return `<div><h2>${informe.modo === "adelante" ? "Hacia adelante" : "Hacia atrás"}</h2><p>${escapar(informe.resumen.mensaje ?? informe.resumen)}</p><p><strong>${informe.objetivo.id}:</strong> ${escapar(informe.objetivo.etiqueta)}</p>${informe.conflictos.map(c => `<p class="aviso error">${c.id}: ${escapar(c.mensaje)}</p>`).join("")}<p><strong>Resultados:</strong> ${informe.resultados.map(r => r.id).join(", ") || "ninguno"}.</p><p><strong>Preguntas consultadas:</strong> ${informe.preguntas_consultadas.join(", ") || "ninguna"}.</p><p><strong>Datos faltantes:</strong> ${informe.faltantes.join(", ") || "ninguno"}.</p><p><strong>Calidad:</strong> ${escapar(informe.calidad.nivel)}.</p><details><summary>Ver la secuencia de reglas y sus fuentes</summary>${pintarTraza(informe.traza)}</details></div>`;
}

/** Ejecuta o compara usando exactamente el conjunto de hechos capturado. */
async function procesar(comparacion = false) {
  if (ocupado) return;
  establecerCarga(true); seleccionar("#error-laboratorio").hidden = true;
  try {
    const datos = {hechos: capturarHechos(), modo: seleccionar("#modo").value, objetivo: seleccionar("#objetivo").value};
    const informe = await solicitar(comparacion ? "/api/comparar" : "/api/inferir", datos);
    seleccionar("#salida").innerHTML = comparacion
      ? `<div class="completo"><h2>Comparación de la meta ${datos.objetivo}</h2><p>${escapar(informe.nota)}</p><p><strong>${informe.coinciden ? "Los mecanismos coinciden en el sustento de la meta." : "Se detectó una diferencia."}</strong></p></div>${resumir(informe.adelante)}${resumir(informe.atras)}`
      : resumir(informe);
    seleccionar("#salida").hidden = false;
  } catch (error) { seleccionar("#salida").hidden = true; mostrarError(error); } finally { establecerCarga(false); }
}

/** Carga un caso; los casos de "todo Desconozco" dejan los selectores vacíos. */
function cargarCaso() {
  const caso = casos.find(c => c.id === seleccionar("#caso").value);
  seleccionar("#salida").hidden = true; seleccionar("#error-laboratorio").hidden = true;
  if (!caso) return;
  presentarEntradas(caso.todo_d ? {} : caso.hechos);
  if (caso.objetivo) seleccionar("#objetivo").value = caso.objetivo;
}

/** Ejecuta los casos del documento en el servidor y pinta esperado contra obtenido. */
async function ejecutarTodos() {
  if (ocupado) return;
  establecerCarga(true); seleccionar("#error-laboratorio").hidden = true;
  try {
    const lista = await solicitar("/api/casos/ejecutar");
    const pasan = lista.filter(c => c.ok).length;
    seleccionar("#tabla-casos").innerHTML = `<p><strong class="${pasan === lista.length ? "pasa" : "falla"}">${pasan} de ${lista.length} casos pasan.</strong></p><div class="envoltura-tabla"><table class="tabla-casos"><thead><tr><th>Caso</th><th>Resultado</th><th>Obtenido</th></tr></thead><tbody>${lista.map(c => `<tr><td><strong>${c.id}</strong> ${escapar(c.nombre)}</td><td class="${c.ok ? "pasa" : "falla"}">${c.ok ? "Pasa" : "Falla"}${c.diferencias.map(d => `<br><small>${escapar(d)}</small>`).join("")}</td><td class="obtenido">${escapar(c.obtenido)}</td></tr>`).join("")}</tbody></table></div>`;
  } catch (error) { mostrarError(error); } finally { establecerCarga(false); }
}

/** Carga entradas, reglas, fuentes y los casos verificables del documento. */
async function iniciar() {
  iniciarTema(); establecerCarga(true);
  try {
    [base, casos] = await Promise.all([solicitar("/api/base"), solicitar("/api/casos")]);
    seleccionar("#caso").innerHTML = '<option value="">Datos propios</option>' + casos.map(c => `<option value="${c.id}">${c.id} · ${escapar(c.nombre)}</option>`).join("");
    seleccionar("#objetivo").innerHTML = [...base.recomendaciones, ...base.conclusiones].map(e => `<option value="${e.id}">${e.id} · ${escapar(e.titulo || e.descripcion)}</option>`).join("");
    seleccionar("#objetivo").value = "A01"; presentarEntradas();
    seleccionar("#catalogo").innerHTML = base.reglas.map(r => `<article class="catalogo-regla"><strong>${r.id}</strong> · <code>${escapar(r.expresion)} → ${r.entonces}</code><p>${escapar(r.explicacion)}</p></article>`).join("") + `<h2>Fuentes</h2>${base.fuentes.map(f => `<p class="texto-secundario"><strong>${f.id}</strong> ${escapar(f.referencia)}</p>`).join("")}`;
  } catch (error) { mostrarError(error); } finally { establecerCarga(false); }
}
seleccionar("#ejecutar").addEventListener("click", () => procesar(false));
seleccionar("#comparar").addEventListener("click", () => procesar(true));
seleccionar("#ejecutar-todos").addEventListener("click", ejecutarTodos);
seleccionar("#caso").addEventListener("change", cargarCaso);
seleccionar("#reiniciar").addEventListener("click", () => { if (ocupado || !base) return; presentarEntradas(); seleccionar("#caso").value = ""; seleccionar("#salida").hidden = true; seleccionar("#error-laboratorio").hidden = true; });
iniciar();
