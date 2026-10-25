"use strict";
const $ = selector => document.querySelector(selector);
const esc = value => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const etiquetas = {V:"Sí",F:"No",D:"Desconozco"};
// Redacción breve de presentación; el significado y la regla originales se
// conservan en la base de conocimientos y en el detalle del razonamiento.
const resumenes = {C20:"Posible presencia de algas",C27:"Posible problema de oxigenación",C28:"La temperatura podría influir en el apetito de los peces",C29:"Posible funcionamiento insuficiente del biofiltro",C30:"Posible desequilibrio de nutrientes para las lechugas"};
let temas = [], preguntas = {}, hechos = {}, tema = null, resultado = null, ocupado = false;
const iconos = {
  peces:'<path d="M7 16c5-9 12-9 19 0-7 9-14 9-19 0Z"/><path d="m7 16-5-5v10l5-5"/><circle cx="21" cy="15" r="1"/>',
  planta:'<path d="M16 28V14M16 20C5 20 4 12 4 7c9 0 12 5 12 13ZM16 14C16 5 23 3 29 3c0 8-5 13-13 11Z"/>',
  agua:'<path d="M16 3C12 10 6 15 6 21a10 10 0 0 0 20 0C26 15 20 10 16 3Z"/><path d="M11 21a5 5 0 0 0 5 5"/>',
  buscar:'<circle cx="13" cy="13" r="9"/><path d="m20 20 9 9M13 9v8M9 13h8"/>'
};
/** Solicita datos al servidor y convierte la respuesta JSON. */
async function solicitarAPI(ruta,contenidoPeticion) {
  const respuesta = await fetch(ruta,contenidoPeticion === undefined ? {} : {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(contenidoPeticion)});
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new Error(datos.error || "No se pudo completar la consulta.");
  return datos;
}
/** Deshabilita controles mientras se actualiza una consulta. */
function marcarOcupado(value) {
  ocupado=value;
  document.querySelectorAll("button,select").forEach(el => {el.disabled=value;});
  $("#consultation").setAttribute("aria-busy",String(value));
}
/** Presenta un error sin borrar las respuestas introducidas. */
function mostrarError(error) {
  $("#error-texto").textContent=`No pudimos actualizar la consulta. Tus respuestas siguen aquí. ${error.message}`;
  $("#error").hidden=false;
}
/** Solicita nuevamente el razonamiento con los hechos vigentes. */
async function actualizar() {
  if(ocupado) return;
  marcarOcupado(true); $("#error").hidden=true;
  try {
    resultado=await solicitarAPI("/api/consultar",{hechos,tema:tema.id});
    mostrar();
  } catch(error) {
    resultado=null;
    $("#pregunta-tarjeta").hidden=false;
    $("#pregunta-tarjeta").innerHTML='<h2>Conexión pendiente</h2><p class="small">Vuelve a intentar para continuar con tus respuestas.</p>';
    $("#outcome").hidden=true; $("#technical").hidden=true;
    mostrarHistorial(); mostrarError(error);
  } finally {marcarOcupado(false);}
}
/** Abre una consulta con los hechos iniciales del tema elegido. */
function iniciarConsulta(perfil) {
  if(ocupado) return;
  tema=perfil; hechos={...perfil.hechos}; resultado=null;
  $("#welcome").hidden=true; $("#consultation").hidden=false;
  $("#tema-titulo").textContent=tema.titulo;
  $("#history").open=false; $("#technical").open=false;
  $("#pregunta-tarjeta").innerHTML='<p class="loading">Preparando tu consulta…</p>';
  actualizar();
}
/** Reinicia la vista y descarta los hechos de la consulta anterior. */
function reiniciarConsulta() {
  if(ocupado) return;
  tema=null; hechos={}; resultado=null;
  $("#consultation").hidden=true; $("#welcome").hidden=false; $("#error").hidden=true;
  $("#pregunta-tarjeta").replaceChildren(); $("#outcome").replaceChildren();
  $("#answers-list").replaceChildren(); $("#technical-content").replaceChildren();
  window.scrollTo({top:0});
}
/** Permite revisar y corregir respuestas previamente registradas. */
function mostrarHistorial() {
  $("#history").hidden=!Object.keys(hechos).length;
  $("#answers-list").innerHTML=Object.entries(hechos).map(([id,value])=>`<div class="answer-row"><label for="answer-${id}">${esc(preguntas[id].texto)}</label><select id="answer-${id}" data-fact="${id}">${Object.entries(etiquetas).map(([v,label])=>`<option value="${v}" ${v===value?'selected':''}>${label}</option>`).join('')}</select></div>`).join('');
  document.querySelectorAll('[data-fact]').forEach(select=>select.addEventListener('change',async ()=>{
    if(ocupado)return;
    hechos[select.dataset.fact]=select.value; await actualizar();
    if(resultado && !resultado.terminada) $('#pregunta-tarjeta').scrollIntoView({block:'start'});
  }));
}
/** Muestra una pregunta pendiente y sus opciones de respuesta. */
function mostrarPregunta() {
  const tarjeta=$("#pregunta-tarjeta");
  if(resultado.conflictos.length) {
    tarjeta.innerHTML=`<span class="step-label">UNA COMPROBACIÓN ANTES DE SEGUIR</span><h2>Estas respuestas no coinciden</h2><p class="small">Comprueba que se refieran a la misma muestra o período.</p>${[...new Set(resultado.conflictos.flatMap(c=>c.hechos))].map(id=>`<div class="conflict-pregunta">${esc(preguntas[id].texto)}<strong>Respondiste: ${etiquetas[hechos[id]]}</strong></div>`).join('')}<button class="secondary" id="review-conflict">Corregir mis respuestas</button>`;
    $('#review-conflict').addEventListener('click',()=>{$('#history').open=true; $('#history').scrollIntoView({block:'start'}); $('#answers-list select').focus();});
    return;
  }
  const q=preguntas[resultado.pregunta_siguiente];
  tarjeta.innerHTML=`<span class="step-label">${esc(q.categoria)}</span><h2>${esc(q.texto)}</h2><div class="answer-buttons"><button data-answer="V">Sí</button><button data-answer="F">No</button><button data-answer="D">Desconozco</button></div><details class="ayuda"><summary>¿Cómo puedo comprobarlo?</summary><div>${mostrarAyuda(q.ayuda)}</div></details>`;
  document.querySelectorAll('[data-answer]').forEach(button=>button.addEventListener('click',()=>{
    if(ocupado)return;
    hechos[q.id]=button.dataset.answer; actualizar();
  }));
}
/** Recorre la traza para recuperar hechos que justifican un resultado. */
function obtenerEvidencias(id,seen=new Set()) {
  if(seen.has(id))return [];
  const siguiente=new Set([...seen,id]);
  return resultado.traza.filter(s=>s.conclusion===id).flatMap(s=>Object.entries(s.premisas).flatMap(([key,value])=>{
    if(preguntas[key]) return value==='D'?[]:[`${preguntas[key].texto} — ${etiquetas[value]}`];
    return value==='V'?obtenerEvidencias(key,siguiente):[];
  }));
}
/** Genera una explicación breve a partir de hechos observados. */
function explicarRazon(id) {
  const elementos=[...new Set(obtenerEvidencias(id))];
  return `<details class="explicacion"><summary>¿Por qué lo sugerimos?</summary><p>Se apoya en estas respuestas:</p><ul>${elementos.map(texto=>`<li>${esc(texto)}</li>`).join('')}</ul><p>Puedes consultar las reglas y fuentes en el detalle del razonamiento.</p></details>`;
}
/** Presenta una verificación y su explicación opcional. */
function mostrarRecomendacion(item) {
  return `<div class="mostrarRecomendacion"><span class="check" aria-hidden="true">✓</span><div>${esc(item.descripcion)}${explicarRazon(item.id)}</div></div>`;
}
/** Agrupa los problemas y las verificaciones de la consulta. */
function mostrarResultado() {
  const recomendadas=resultado.recomendaciones;
  $('#outcome').innerHTML=`<div class="resultado-heading"><span class="resultado-simbolo" aria-hidden="true">${resultado.resultados.length?'✓':'?'}</span><h1>${esc(resultado.titulo)}</h1><p>${esc(resultado.resumen)}</p></div>
  ${resultado.hipotesis.length?`<section class="findings"><h2>Posibles problemas</h2>${resultado.hipotesis.map(item=>`<div class="finding">${esc(resumenes[item.id]||item.descripcion)}${explicarRazon(item.id)}</div>`).join('')}</section>`:''}
  ${recomendadas.length?`<section class="recomendaciones"><h2>Qué puedes revisar ahora</h2>${recomendadas.slice(0,3).map(mostrarRecomendacion).join('')}${recomendadas.length>3?`<details class="more"><summary>Ver otras verificaciones relacionadas</summary>${recomendadas.slice(3).map(mostrarRecomendacion).join('')}</details>`:''}</section>`:''}
  ${resultado.condiciones.length?`<details class="history"><summary>Ver las condiciones observadas</summary>${resultado.condiciones.map(item=>`<p class="small">${esc(item.descripcion)}</p>`).join('')}</details>`:''}
  ${resultado.sin_resolver.length?'<p class="uncertain">Quedaron aspectos sin aclarar por falta de información. Puedes revisar las respuestas «Desconozco» si consigues esos datos.</p>':''}
  <p class="scope">${esc(resultado.nota_alcance)}</p><div class="resultado-actions"><button id="new-consult" class="primary">Revisar otro problema</button><button id="download" class="secondary">Guardar resultado</button></div>`;
  $('#new-consult').addEventListener('click',reiniciarConsulta);
  $('#download').addEventListener('click',()=>{
    if(!resultado)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(resultado,null,2)],{type:'application/json'}));
    const enlace=document.createElement('a');enlace.href=url;enlace.download='consulta-acuaponia.json';enlace.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
}
/** Presenta reglas activadas y comparación de razonamientos. */
function mostrarDetallesTecnicos() {
  const a=resultado.analisis;
  $('#technical-content').innerHTML=`<div class="small"><p>El sistema combina ambos mecanismos automáticamente. Primero deriva resultados de los hechos y luego busca las premisas que faltan en las metas relacionadas con el caso.</p><p><strong>Reglas activadas hacia adelante:</strong> ${a.reglas_adelante.join(', ')||'Ninguna'}.</p><p><strong>Reglas activadas hacia atrás:</strong> ${a.reglas_atras.join(', ')||'Ninguna'}.</p><p><strong>Preguntas aún pertinentes:</strong> ${a.preguntas_sugeridas.join(', ')||'Ninguna'}.</p><table><thead><tr><th>Meta</th><th>Adelante: sustentada</th><th>Atrás</th></tr></thead><tbody>${a.comparaciones.map(c=>`<tr><td>${c.objetivo}</td><td>${c.sustentada_adelante?'Sí':'No derivada'}</td><td>${({V:'Sustentada',F:'No sustentable',D:'Indeterminada'})[c.estado_atras]}</td></tr>`).join('')}</tbody></table><p>«No derivada» no significa falsa. La comparación usa los mismos hechos y la misma base. No se calculan probabilidades.</p></div><h3>Cómo se obtuvieron los resultados</h3>${resultado.traza.map(step=>`<div class="traza-step"><strong>${step.regla} · ${step.conclusion}</strong><p>${esc(step.expresion)}</p><p>Premisas: ${Object.entries(step.premisas).map(([key,value])=>`${key}=${value}`).join(', ')}</p><p>${esc(step.explicacion)}</p></div>`).join('')||'<p class="small">Ninguna regla se activó con estas respuestas.</p>'}`;
}
/** Actualiza las secciones visibles según el estado de la consulta. */
function mostrar() {
  $('#pregunta-tarjeta').hidden=resultado.terminada;
  $('#outcome').hidden=!resultado.terminada;
  $('#technical').hidden=!resultado.terminada;
  if(resultado.terminada)mostrarResultado(); else mostrarPregunta();
  mostrarHistorial(); mostrarDetallesTecnicos();
}
/** Carga los catálogos y registra los controles de la interfaz. */
async function inicializar() {
  marcarOcupado(true);
  try {
    const [catalog,profiles]=await Promise.all([solicitarAPI('/api/conocimientos'),solicitarAPI('/api/temas')]);
    preguntas=Object.fromEntries(catalog.preguntas.map(q=>[q.id,q]));temas=profiles;
    $('#temas').innerHTML=temas.map(p=>`<button class="tema" data-tema="${esc(p.id)}"><span class="icon" aria-hidden="true"><svg viewBox="0 0 32 32">${iconos[p.icono]||iconos.buscar}</svg></span><span><strong>${esc(p.titulo)}</strong><small>${esc(p.descripcion)}</small></span><span class="arrow" aria-hidden="true">→</span></button>`).join('');
    document.querySelectorAll('[data-tema]').forEach(button=>button.addEventListener('click',()=>iniciarConsulta(temas.find(p=>p.id===button.dataset.tema))));
    $('#error').hidden=true;
  }catch(error){$('#temas').textContent='La consulta estará disponible al recuperar la conexión.';mostrarError(error);}finally{marcarOcupado(false);}
}
$('#reiniciarConsulta').addEventListener('click',reiniciarConsulta);
$('#retry').addEventListener('click',()=>tema?actualizar():inicializar());
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
