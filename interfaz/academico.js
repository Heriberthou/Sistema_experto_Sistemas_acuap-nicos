/* La interfaz captura respuestas; toda inferencia se ejecuta en Python. */
"use strict";
const $ = (selector) => document.querySelector(selector);
const escaparHTML = (value) => String(value).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const etiquetas = {V:"Sí", F:"No", D:"Desconozco"};
let baseConocimientos, ejemplos, hechos = {}, modo = "adelante", objetivo = "C27", resultado, ocupado = false;
let indicePreguntas, indiceResultados;

/** Solicita datos al servidor y convierte la respuesta JSON. */
async function solicitarAPI(ruta, contenidoPeticion) {
  const respuesta = await fetch(ruta, contenidoPeticion === undefined ? {} : {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(contenidoPeticion)
  });
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new Error(datos.error || "No se pudo completar la consulta.");
  return datos;
}

/** Presenta un error sin borrar las respuestas introducidas. */
function mostrarError(error) {
  $("#error").textContent = `No se pudo actualizar el análisis. ${error.message} Comprueba que el servidor Python esté disponible.`;
  $("#error").hidden = false;
}

/** Deshabilita controles mientras se actualiza una consulta. */
function marcarOcupado(value) {
  ocupado = value;
  document.querySelectorAll("#consult button, #consult select, #consult input, [data-example]").forEach((element) => {element.disabled = value;});
  $("#consult").setAttribute("aria-busy", String(value));
}

/** Solicita nuevamente el razonamiento con los hechos vigentes. */
async function actualizar() {
  marcarOcupado(true);
  $("#error").hidden = true;
  $("#comparacion").hidden = true;
  try {
    resultado = await solicitarAPI("/api/inferir", {hechos, modo, objetivo});
    mostrar();
  } catch (error) {
    resultado = null;
    $("#resultados").innerHTML = '<p class="muted">El análisis no está disponible. Tus respuestas siguen en esta pestaña; vuelve a intentarlo.</p><button class="button secondary" id="retry">Reintentar análisis</button>';
    $("#retry").addEventListener("click", actualizar);
    $("#traza").replaceChildren();
    $("#conflictos").replaceChildren();
    $("#objetivo-estado").replaceChildren();
    $("#pregunta-content").textContent = "Análisis pendiente de conexión. Reintenta para continuar.";
    $("#resultado-count").textContent = "—";
    $("#regla-count").textContent = "—";
    $("#traza-count").textContent = "0";
    mostrarHechos();
    mostrarError(error);
  } finally { marcarOcupado(false); }
}

/** Muestra una pregunta pendiente y sus opciones de respuesta. */
function mostrarPregunta() {
  const siguiente = indicePreguntas[resultado.preguntas_siguientes[0]];
  if (!siguiente) {
    $("#pregunta-content").innerHTML = `<span class="tag">CONSULTA ACTUAL</span><h3>${resultado.conflictos.length ? "Revisa las respuestas en conflicto" : "No hay nuevas preguntas para esta consulta"}</h3><p class="muted">${resultado.objetivo.estado === "D" ? "La información pendiente puede mantener resultados indeterminados. Puedes revisar las respuestas Desconozco o explorar otro objetivo." : "Puedes revisar tus respuestas, elegir otro objetivo o iniciar una nueva consulta."}</p>`;
    return;
  }
  $("#pregunta-content").innerHTML = `<div class="pregunta-meta"><span class="tag">${escaparHTML(siguiente.categoria)}</span><span class="pregunta-id">${siguiente.id}</span></div><h3>${escaparHTML(siguiente.texto)}</h3><p class="muted">${modo === "atras" ? `Esta respuesta ayuda a investigar ${objetivo}.` : "Pregunta seleccionada por su participación en resultados aún pendientes."}</p><div class="answers"><button class="answer" data-answer="V">✓ Sí</button><button class="answer" data-answer="F">✕ No</button><button class="answer" data-answer="D">? Desconozco</button></div><details class="ayuda"><summary>¿Cómo puedo comprobarlo?</summary><div>${mostrarAyuda(siguiente.ayuda)}</div></details>`;
  document.querySelectorAll("[data-answer]").forEach((button) => button.addEventListener("click", async () => {
    if (ocupado) return;
    hechos[siguiente.id] = button.dataset.answer;
    await actualizar();
  }));
}

/** Muestra los hechos editables del catálogo seleccionado. */
function mostrarHechos() {
  const categoria = $("#categoria").value;
  $("#hechos-count").textContent = Object.keys(hechos).length;
  $("#answered-count").textContent = `${Object.keys(hechos).length} / ${baseConocimientos.preguntas.length}`;
  $("#hechos-list").innerHTML = baseConocimientos.preguntas.filter((q) => !categoria || q.categoria === categoria).map((q) => `<div class="fact-row"><label for="fact-${q.id}"><span>${q.id} · ${escaparHTML(q.categoria)}</span>${escaparHTML(q.texto)}</label><select id="fact-${q.id}" data-fact="${q.id}"><option value="">Sin responder</option>${Object.entries(etiquetas).map(([value, label]) => `<option value="${value}" ${hechos[q.id] === value ? "selected" : ""}>${label}</option>`).join("")}</select></div>`).join("");
  document.querySelectorAll("[data-fact]").forEach((select) => select.addEventListener("change", async () => {
    if (ocupado) return;
    if (select.value) hechos[select.dataset.fact] = select.value;
    else delete hechos[select.dataset.fact];
    await actualizar();
  }));
}

/** Describe un hecho utilizado en una regla. */
function premisaHTML(key, value) {
  return `<li><strong>${key} = ${value}</strong> · ${escaparHTML(indicePreguntas[key]?.texto || indiceResultados[key]?.descripcion || key)}</li>`;
}

/** Reconstruye las reglas que justifican una conclusión. */
function demostracionHTML(id, seen = new Set()) {
  if (seen.has(id)) return "";
  const siguiente = new Set([...seen, id]);
  return resultado.traza.filter((step) => step.conclusion === id).map((step) => `<div class="proof"><p><strong>${step.regla}</strong> · ${escaparHTML(step.expresion)} → ${step.conclusion}</p><ul>${Object.entries(step.premisas).map(([key,value]) => premisaHTML(key,value)).join("")}</ul><p>${escaparHTML(step.explicacion)}</p>${Object.entries(step.premisas).filter(([key,value]) => value === "V" && indiceResultados[key]).map(([key]) => demostracionHTML(key, siguiente)).join("")}</div>`).join("");
}

/** Actualiza las secciones visibles según el estado de la consulta. */
function mostrar() {
  $("#resultado-count").textContent = resultado.resultados.length;
  $("#regla-count").textContent = resultado.traza.length;
  $("#traza-count").textContent = resultado.traza.length;
  $("#modo-ayuda").textContent = modo === "adelante" ? "Se buscarán todas las conclusiones que permitan tus respuestas." : "Se recorrerán solo las reglas que pueden sustentar el objetivo y sus dependencias.";
  $("#conflictos").innerHTML = resultado.conflictos.map((conflict) => `<div class="conflict"><strong>Respuestas incompatibles</strong><p>${escaparHTML(conflict.message)}</p>${conflict.hechos.map((id) => `<button data-review="${id}">Revisar ${id}</button>`).join("")}<p>Estas respuestas se tratan como desconocidas hasta que las corrijas. Los indicios independientes siguen evaluándose.</p></div>`).join("");
  document.querySelectorAll("[data-review]").forEach((button) => button.addEventListener("click", () => {
    $(".hechos-panel").open = true;
    $("#categoria").value = "";
    mostrarHechos();
    const control = $(`#fact-${button.dataset.review}`);
    control.focus();
    control.scrollIntoView({behavior:"smooth",block:"center"});
  }));
  $("#objetivo-estado").innerHTML = `<div class="objetivo-box"><strong>${objetivo} · ${escaparHTML(resultado.objetivo.etiqueta)}</strong>${escaparHTML(indiceResultados[objetivo].descripcion)}${resultado.objetivo.faltantes.length ? `<p>Datos pendientes: ${resultado.objetivo.faltantes.join(", ")}. Una respuesta D requiere revisión manual si obtienes nueva información.</p>` : ""}${resultado.objetivo.estado === "F" ? "<p>Esto no significa que la condición sea imposible en un sistema real.</p>" : ""}</div>`;
  const groups = [["Condición","Condiciones observadas"],["Hipótesis","Hipótesis compatibles"],["Verificación","Verificaciones recomendadas"]];
  $("#resultados").innerHTML = resultado.resultados.length ? groups.map(([tipo, label]) => {
    const elementos = resultado.resultados.filter((r) => r.tipo === tipo);
    return elementos.length ? `<h3 class="resultado-group">${label} · ${elementos.length}</h3>${elementos.map((item) => `<article class="resultado-item ${tipo === "Hipótesis" ? "hypothesis" : ""}"><span class="tag">${item.id} · ${escaparHTML(tipo)}</span><h3>${escaparHTML(item.descripcion)}</h3><details><summary>¿Por qué aparece? ${item.justificaciones.join(", ")}</summary>${demostracionHTML(item.id)}</details></article>`).join("")}` : "";
  }).join("") : `<div class="empty"><span class="empty-icon">◎</span><h3>${Object.keys(hechos).length ? "Todavía no hay resultados sustentados" : "El análisis comienza contigo"}</h3><p>${escaparHTML(resultado.resumen)} Responde una observación o carga un caso de ejemplo.</p></div>`;
  $("#traza").innerHTML = resultado.traza.map((step, i) => `<article class="traza-item"><span class="tag">PASO ${i+1} · ${step.regla}</span><p><code>${escaparHTML(step.expresion)} → ${step.conclusion}</code></p><p>Premisas: ${Object.entries(step.premisas).map(([key,value]) => `${key}=${value}`).join(" · ")}</p><p>${escaparHTML(step.explicacion)}</p></article>`).join("") || '<p class="muted">Aún no se han activado reglas.</p>';
  mostrarPregunta();
  mostrarHechos();
}

/** Cambia entre las secciones del laboratorio académico. */
function cambiarVista(view) {
  document.querySelectorAll(".view").forEach((section) => {section.hidden = section.id !== view;});
  document.querySelectorAll(".nav").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
    if (button.dataset.view === view) { button.setAttribute("aria-current","page"); $("#breadcrumb").textContent = button.textContent.slice(2).trim(); }
    else button.removeAttribute("aria-current");
  });
  window.scrollTo({top:0,behavior:"smooth"});
}

/** Filtra y muestra las reglas de la base de conocimientos. */
function mostrarReglas() {
  const query = $("#regla-buscar").value.toLocaleLowerCase("es");
  const reglas = baseConocimientos.reglas.filter((regla) => `${regla.id} ${regla.expresion} ${regla.explicacion} ${indiceResultados[regla.conclusion].descripcion}`.toLocaleLowerCase("es").includes(query));
  $("#reglas-list").innerHTML = reglas.map((regla) => `<article class="tarjeta"><span class="tag">${regla.id}</span><h3>${escaparHTML(indiceResultados[regla.conclusion].descripcion)}</h3><code>SI ${escaparHTML(regla.expresion)} → ${regla.conclusion}</code><p>${escaparHTML(regla.explicacion)}</p></article>`).join("") || '<p class="muted">No hay reglas que coincidan con la búsqueda.</p>';
}

/** Carga los catálogos y registra los controles de la interfaz. */
async function inicializar() {
  try {
    [baseConocimientos, ejemplos] = await Promise.all([solicitarAPI("/api/conocimientos"), solicitarAPI("/api/ejemplos")]);
    indicePreguntas = Object.fromEntries(baseConocimientos.preguntas.map((q) => [q.id,q]));
    indiceResultados = Object.fromEntries([...baseConocimientos.conclusiones,...baseConocimientos.recomendaciones].map((c) => [c.id,c]));
    $("#objetivo").innerHTML = Object.values(indiceResultados).map((c) => `<option value="${c.id}" ${c.id === objetivo ? "selected" : ""}>${c.id} · ${escaparHTML(c.descripcion)}</option>`).join("");
    [...new Set(baseConocimientos.preguntas.map((q) => q.categoria))].forEach((categoria) => $("#categoria").add(new Option(categoria,categoria)));
    $("#fuentes-list").innerHTML = baseConocimientos.fuentes.map((fuente) => `<article class="source"><strong>${fuente.id} · ${escaparHTML(fuente.referencia)}</strong><p>${escaparHTML(fuente.uso)}</p><small>${escaparHTML(fuente.verificacion)}</small></article>`).join("");
    $("#ejemplos-list").innerHTML = ejemplos.map((example, index) => `<article class="tarjeta"><span class="tag">CASO ${String(index+1).padStart(2,"0")}</span><h2>${escaparHTML(example.nombre)}</h2><p>${escaparHTML(example.descripcion)}</p><p class="muted">Esperado hacia adelante: ${example.esperados.join(", ")}<br>Reglas: ${example.reglas_esperadas.join(", ")}</p><button class="button" data-example="${example.id}">Explorar este caso →</button></article>`).join("");
    document.querySelectorAll("[data-example]").forEach((button) => button.addEventListener("click", async () => {
      if (ocupado) return;
      const example = ejemplos.find((item) => item.id === button.dataset.example);
      hechos = {...example.hechos}; objetivo = example.objetivo; modo = "adelante";
      $("#objetivo").value = objetivo;
      $('input[name="modo"][value="adelante"]').checked = true;
      cambiarVista("consult");
      await actualizar();
    }));
    document.querySelectorAll(".nav").forEach((button) => button.addEventListener("click", () => cambiarVista(button.dataset.view)));
    document.querySelectorAll('input[name="modo"]').forEach((input) => input.addEventListener("change", async () => {modo = input.value; await actualizar();}));
    $("#objetivo").addEventListener("change", async (event) => {objetivo = event.target.value; await actualizar();});
    $("#categoria").addEventListener("change", mostrarHechos);
    $("#regla-buscar").addEventListener("input", mostrarReglas);
    $("#reset").addEventListener("click", async () => {hechos = {}; $(".hechos-panel").open = false; await actualizar();});
    $("#compare").addEventListener("click", async () => {
      marcarOcupado(true);
      try {
        const comparacion = await solicitarAPI("/api/comparar", {hechos,objetivo});
        const adelante = comparacion.adelante, back = comparacion.atras;
        const filasComparacion = [["Estado de la meta",adelante.objetivo.etiqueta,back.objetivo.etiqueta],["Resultados",adelante.resultados.length,back.resultados.length],["Reglas activadas",adelante.traza.length,back.traza.length],["Reglas consideradas",adelante.reglas_examinadas.length,back.reglas_examinadas.length],["Preguntas sugeridas",adelante.preguntas_siguientes.length,back.preguntas_siguientes.length]];
        $("#comparacion").innerHTML = `<h3>Comparación para ${objetivo}</h3><p class="muted">${escaparHTML(comparacion.nota)}</p><table class="comparacion-table"><thead><tr><th>Medida</th><th>Adelante</th><th>Atrás</th></tr></thead><tbody>${filasComparacion.map(([a,b,c]) => `<tr><th>${a}</th><td>${escaparHTML(b)}</td><td>${escaparHTML(c)}</td></tr>`).join("")}</tbody></table><p class="muted">${comparacion.misma_meta ? "Ambos mecanismos coinciden en el sustento del objetivo." : "Los mecanismos difieren; revisa la traza."}</p><details class="comparacion-detail"><summary>Ver reglas y preguntas de cada mecanismo</summary><p><strong>Adelante · reglas:</strong> ${adelante.traza.map((s) => s.regla).join(", ") || "Ninguna"}</p><p><strong>Atrás · reglas:</strong> ${back.traza.map((s) => s.regla).join(", ") || "Ninguna"}</p><p><strong>Adelante · preguntas sugeridas:</strong> ${adelante.preguntas_siguientes.join(", ") || "Ninguna"}</p><p><strong>Atrás · preguntas sugeridas:</strong> ${back.preguntas_siguientes.join(", ") || "Ninguna"}</p></details>`;
        $("#comparacion").hidden = false;
      } catch (error) {mostrarError(error);} finally {marcarOcupado(false);}
    });
    $("#export").addEventListener("click", () => {
      if (!resultado) return;
      const archivoBinario = new Blob([JSON.stringify({version:1,exported_at:new Date().toISOString(),...resultado},null,2)],{type:"application/json"});
      const url = URL.createObjectURL(archivoBinario);
      const enlace = document.createElement("a"); enlace.href = url; enlace.download = "consulta-acuaponia.json"; enlace.click();
      setTimeout(() => URL.revokeObjectURL(url),1000);
    });
    mostrarReglas();
    await actualizar();
  } catch (error) {mostrarError(error);}
}
inicializar();

/** Presenta los campos disponibles de una ayuda, escapando el texto recibido. */
function mostrarAyuda(ayuda) {
  if (!ayuda) return "<p>No hay información adicional para esta pregunta.</p>";
  if (typeof ayuda === "string") return `<p>${esc(ayuda)}</p>`;
  const escapar = typeof escaparHTML === "function" ? escaparHTML : esc;
  const elementos = [];
  if (ayuda.descripcion) elementos.push(`<p>${escapar(ayuda.descripcion)}</p>`);
  if (ayuda.unidad) elementos.push(`<p><strong>Unidad:</strong> ${escapar(ayuda.unidad)}</p>`);
  if (ayuda.ejemplo_si) elementos.push(`<p><strong>Ejemplo de Sí:</strong> ${escapar(ayuda.ejemplo_si)}</p>`);
  if (ayuda.ejemplo_no) elementos.push(`<p><strong>Ejemplo de No:</strong> ${escapar(ayuda.ejemplo_no)}</p>`);
  if (ayuda.advertencia) elementos.push(`<p><strong>Importante:</strong> ${escapar(ayuda.advertencia)}</p>`);
  return elementos.join("");
}
