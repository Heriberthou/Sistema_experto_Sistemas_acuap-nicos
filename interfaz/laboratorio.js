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

/** Un selector Sí/No/Desconozco; las respondidas se resaltan para distinguirlas de las demás. */
function entrada(p, valor) {
  return `<label class="entrada-laboratorio valor-${valor}"><span>${p.id}</span><small>${escapar(p.texto)}</small><select data-hecho="${p.id}">${[["D", "Desconozco"], ["V", "Sí"], ["F", "No"]].map(([v, texto]) => `<option value="${v}" ${valor === v ? "selected" : ""}>${texto}</option>`).join("")}</select></label>`;
}

/** Muestra primero las preguntas con respuesta (Sí/No) y deja el resto plegado, para no marear. */
function presentarEntradas(hechos = {}, abierto = false) {
  const respondidas = base.preguntas.filter(p => ["V", "F"].includes(hechos[p.id]));
  const pendientes = base.preguntas.filter(p => !["V", "F"].includes(hechos[p.id]));
  seleccionar("#entradas").innerHTML = `<div class="respondidas"><p class="grupo-laboratorio">Con respuesta (${respondidas.length})</p>${respondidas.length
    ? `<div class="rejilla-entradas">${respondidas.map(p => entrada(p, hechos[p.id])).join("")}</div>`
    : '<p class="texto-secundario">Todavía no hay respuestas. Elige un caso o abre «Preguntas sin responder» para contestar.</p>'}</div>
    <details class="sin-responder" ${abierto || !respondidas.length ? "open" : ""}><summary>Preguntas sin responder (${pendientes.length}) · cuentan como «Desconozco»</summary>${Object.entries(GRUPOS).map(([grupo, datos]) => {
      const lista = pendientes.filter(p => p.grupo === grupo);
      return lista.length ? `<p class="grupo-laboratorio">${escapar(datos.nombre)}</p><div class="rejilla-entradas">${lista.map(p => entrada(p, "D")).join("")}</div>` : "";
    }).join("")}</details>`;
}

/** Lee las entradas; solo viajan las respuestas distintas de Desconozco. */
function capturarHechos() {
  return Object.fromEntries(base.preguntas.map(p => [p.id, seleccionar(`[data-hecho="${p.id}"]`).value]).filter(([, v]) => v !== "D"));
}

const SINO = {V: "Sí", F: "No", D: "Desconozco"};

/** Árbol de razonamiento con dirección y orden: el mismo árbol se recorre distinto según el mecanismo. */
function arbol(informe) {
  const adelante = informe.modo === "adelante", pasos = informe.traza, porSalida = new Map();
  pasos.forEach((paso, i) => { if (!porSalida.has(paso.conclusion)) porSalida.set(paso.conclusion, {...paso, indice: i}); });
  const titulo = id => { const e = [...base.conclusiones, ...base.recomendaciones].find(x => x.id === id); return e ? (e.titulo || e.descripcion) : id; };
  const pregunta = id => base.preguntas.find(p => p.id === id)?.texto || id;
  const meta = informe.objetivo.id;
  if (!porSalida.has(meta)) return `<p class="aviso alerta">La meta ${meta} no se alcanzó con estas respuestas, así que no hay recorrido que mostrar para ella.</p>`;
  // Orden: hacia adelante, el de la traza (de las respuestas a la meta); hacia atrás, de la meta hacia abajo.
  const orden = new Map(), nodos = [];
  const recorrer = (id, ruta = []) => {
    if (ruta.includes(id)) return;
    const paso = porSalida.get(id); nodos.push(id);
    for (const e of paso.evidencias) if (/^[CA]/.test(e.hecho) && porSalida.has(e.hecho)) recorrer(e.hecho, [...ruta, id]);
  };
  recorrer(meta);
  (adelante ? [...nodos].sort((x, y) => porSalida.get(x).indice - porSalida.get(y).indice) : nodos).forEach((id, i) => orden.set(id, i + 1));
  const hoja = e => `<li><div class="nodo nodo-q valor-${e.valor}">${adelante ? '<i class="inicio">Dato · inicio</i>' : '<i class="visto">✓ encontrado</i>'}<b>${e.hecho}</b><span>${escapar(pregunta(e.hecho))}</span><em class="respuesta">${SINO[e.valor] || e.valor}</em></div></li>`;
  const nodo = (id, ruta = [], esRaiz = false) => {
    const paso = porSalida.get(id);
    const hijos = ruta.includes(id) ? [] : paso.evidencias.map(e => /^[CA]/.test(e.hecho) && porSalida.has(e.hecho) ? nodo(e.hecho, [...ruta, id]) : hoja(e));
    const marca = !adelante && esRaiz ? '<i class="inicio">Meta · inicio</i>' : "";
    return `<li class="${esRaiz ? "" : "con-flecha"}"><div class="nodo nodo-${id[0]}"><i class="orden">${orden.get(id)}</i>${marca}<b>${id}</b><span>${escapar(titulo(id))}</span><small>${paso.regla} · <code>${escapar(paso.expresion)}</code></small></div>${hijos.length ? `<ul>${hijos.join("")}</ul>` : ""}</li>`;
  };
  // Recorrido en palabras, con los mismos números que el dibujo.
  const verbo = valor => SINO[valor] || valor;
  const evid = paso => paso.evidencias.map(e => /^Q/.test(e.hecho) ? `${e.hecho} = ${verbo(e.valor)}` : e.hecho).join(" y ");
  const lista = adelante
    ? [...nodos].sort((x, y) => porSalida.get(x).indice - porSalida.get(y).indice).map(id => { const p = porSalida.get(id); return `<li><b>${orden.get(id)}.</b> Con ${evid(p)}, la regla ${p.regla} concluye <b>${id}</b> (${escapar(titulo(id))}).</li>`; })
    : nodos.map(id => { const p = porSalida.get(id); const necesita = p.evidencias.map(e => e.hecho).join(" y "); return `<li><b>${orden.get(id)}.</b> ¿Se cumple <b>${id}</b>? La regla ${p.regla} lo concluye si se cumple ${necesita}.</li>`; })
      .concat([`<li><b>${nodos.length + 1}.</b> Busco esas preguntas en tus respuestas: ${[...new Set(nodos.flatMap(id => porSalida.get(id).evidencias.filter(e => /^Q/.test(e.hecho)).map(e => `${e.hecho} = ${verbo(e.valor)} ✓`)))].join(", ")}. La meta queda sustentada.</li>`]);
  const flujo = adelante
    ? '<p class="flujo flujo-adelante">⬆ <strong>Sentido:</strong> de las respuestas hacia la meta. Empieza abajo, en tus datos.</p>'
    : '<p class="flujo flujo-atras">⬇ <strong>Sentido:</strong> de la meta hacia las respuestas. Empieza arriba, en lo que quieres probar.</p>';
  const usadas = new Set(pasos.flatMap(p => p.evidencias.map(e => e.hecho)));
  const otras = [...porSalida.keys()].filter(id => id !== meta && !usadas.has(id));
  const resto = otras.length ? `<details class="otras-ramas"><summary>Otras conclusiones que también salieron (${otras.length})</summary><p class="texto-secundario">${otras.map(id => `${id} · ${escapar(titulo(id))}`).join("; ")}.</p></details>` : "";
  return `${flujo}<div class="arbol ${adelante ? "sube" : "baja"}"><ul>${nodo(meta, [], true)}</ul></div><ol class="recorrido">${lista.join("")}</ol>${resto}`;
}

/** Resume un mecanismo: lo esencial a la vista, el detalle plegado. */
function resumir(informe) {
  const adelante = informe.modo === "adelante";
  const consultadas = informe.preguntas_consultadas.map(id => { const v = informe.hechos_efectivos?.[id] ?? informe.hechos?.[id] ?? "D"; return `<span class="ficha valor-${v}">${id} · ${SINO[v] || v}</span>`; }).join("");
  return `<div class="bloque-resultado"><h2>${adelante ? "Hacia adelante" : "Hacia atrás"}</h2>
    <p class="texto-secundario">${adelante ? "Parte de tus respuestas y deduce todo lo que se pueda." : "Parte de la meta y solo busca las respuestas que la sustentan."}</p>
    <p class="estado-meta"><strong>${informe.objetivo.id}</strong> ${escapar(informe.objetivo.etiqueta)}</p>
    ${informe.conflictos.map(c => `<p class="aviso error">${c.id}: ${escapar(c.mensaje)}</p>`).join("")}
    <p class="leyenda-arbol">Los números indican el orden en que razona el sistema; el verde es la meta y el azul, las conclusiones intermedias.</p>
    ${arbol(informe)}
    <p><strong>Preguntas que usó:</strong> ${consultadas || "ninguna"}</p>
    <details><summary>Más detalle (calidad, datos faltantes y reglas con sus fuentes)</summary>
      <p><strong>Resultados:</strong> ${informe.resultados.map(r => r.id).join(", ") || "ninguno"}.</p>
      <p><strong>Calidad:</strong> ${escapar(informe.calidad.nivel)}.</p>
      <p><strong>Datos faltantes:</strong> ${informe.faltantes.join(", ") || "ninguno"}.</p>
      ${pintarTraza(informe.traza)}</details></div>`;
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

/** Glosario: qué significa cada código y la lista completa de preguntas, conclusiones, recomendaciones, restricciones y fuentes. */
function glosario() {
  const prefijos = [["Q", "Pregunta que se contesta Sí / No / Desconozco (Q01a, Q01b… son escalones de una misma medición)."], ["C", "Conclusión: lo que el sistema deduce (una condición o hipótesis)."], ["A", "Recomendación o acción que se sugiere al usuario."],
    ["R", "Regla «si… entonces…» que une preguntas y conclusiones."], ["K", "Restricción de consistencia: detecta respuestas contradictorias o apresuradas."], ["F", "Fuente bibliográfica de donde sale una regla."],
    ["T", "Caso de prueba del documento (T1, T2…): respuestas de entrada y resultado esperado."]];
  const tabla = (titulo, filas) => `<details><summary>${titulo} (${filas.length})</summary><table class="tabla-casos"><tbody>${filas.map(([id, texto]) => `<tr><td><strong>${id}</strong></td><td>${escapar(texto)}</td></tr>`).join("")}</tbody></table></details>`;
  return `<table class="tabla-casos"><tbody>${prefijos.map(([c, t]) => `<tr><td><strong>${c}</strong></td><td>${escapar(t)}</td></tr>`).join("")}<tr><td><strong>V · F · D</strong></td><td>Verdadero (Sí), Falso (No) y Desconocido (Desconozco).</td></tr><tr><td><strong>Y · O</strong></td><td>En una regla, «Y» exige que se cumplan todas las condiciones; «O», que se cumpla al menos una.</td></tr></tbody></table>`
    + tabla("Preguntas (Q)", base.preguntas.map(p => [p.id, p.texto])) + tabla("Conclusiones (C)", base.conclusiones.map(c => [c.id, c.titulo])) + tabla("Recomendaciones (A)", base.recomendaciones.map(a => [a.id, a.titulo]))
    + tabla("Restricciones (K)", base.restricciones.map(k => [k.id, k.mensaje])) + tabla("Fuentes (F)", base.fuentes.map(f => [f.id, f.referencia])) + tabla("Casos de prueba (T)", casos.map(c => [c.id, c.nombre]));
}

/** Carga entradas, reglas, fuentes y los casos verificables del documento. */
async function iniciar() {
  iniciarTema(); establecerCarga(true);
  try {
    [base, casos] = await Promise.all([solicitar("/api/base"), solicitar("/api/casos")]);
    seleccionar("#caso").innerHTML = '<option value="">Datos propios</option>' + casos.map(c => `<option value="${c.id}">${c.id} · ${escapar(c.nombre)}</option>`).join("");
    seleccionar("#objetivo").innerHTML = [...base.recomendaciones, ...base.conclusiones].map(e => `<option value="${e.id}">${e.id} · ${escapar(e.titulo || e.descripcion)}</option>`).join("");
    seleccionar("#objetivo").value = "A01"; presentarEntradas();
    seleccionar("#glosario").innerHTML = glosario();
    seleccionar("#catalogo").innerHTML = base.reglas.map(r => `<article class="catalogo-regla"><strong>${r.id}</strong> · <code>${escapar(r.expresion)} → ${r.entonces}</code><p>${escapar(r.explicacion)}</p></article>`).join("") + `<h2>Fuentes</h2>${base.fuentes.map(f => `<p class="texto-secundario"><strong>${f.id}</strong> ${escapar(f.referencia)}</p>`).join("")}`;
  } catch (error) { mostrarError(error); } finally { establecerCarga(false); }
}
seleccionar("#ejecutar").addEventListener("click", () => procesar(false));
seleccionar("#comparar").addEventListener("click", () => procesar(true));
seleccionar("#ejecutar-todos").addEventListener("click", ejecutarTodos);
seleccionar("#caso").addEventListener("change", cargarCaso);
seleccionar("#entradas").addEventListener("change", evento => { if (!evento.target.matches("[data-hecho]") || !base) return; const abierto = seleccionar(".sin-responder")?.open; presentarEntradas(capturarHechos(), abierto); });
seleccionar("#reiniciar").addEventListener("click", () => { if (ocupado || !base) return; presentarEntradas(); seleccionar("#caso").value = ""; seleccionar("#salida").hidden = true; seleccionar("#error-laboratorio").hidden = true; });
iniciar();
