/** Consulta del cliente: presenta las respuestas del servidor Python.
 * No se calculan diagnósticos, umbrales ni inferencias en JavaScript; solo se muestran y se envían respuestas.
 */
import {escapar, solicitar, formatearValor, icono, GRUPOS, SUSTENTO, urgencia, sinTitulo, pintarTraza, descargarInforme, iniciarTema} from "/utilidades.js";

const seleccionar = selector => document.querySelector(selector);
const AREAS = [
  ["agua", "Calidad del agua", "Oxígeno, temperatura, pH, amoníaco, nitrito y nitrato."],
  ["peces", "Tus peces", "Boqueo, apetito y mortalidad."],
  ["equipos", "Bomba y aireación", "Energía, circulación y salida de aire."],
  ["plantas", "Tus lechugas", "Hojas, raíces, crecimiento e insectos."],
];
let base, guia = {partidas: []}, preguntas = {}, conclusiones = {}, recomendaciones = {}, objetivo = null;
let hechos = {}, historial = [], cierre = {descartadas: [], final: null}, continuar = false, resultado = null, ocupado = false, avance = 0;

/** Desactiva los controles mientras se evalúa para evitar respuestas simultáneas. */
function establecerCarga(valor) {
  ocupado = valor;
  document.querySelectorAll("button, input, select").forEach(control => { control.disabled = valor; });
  seleccionar("#consulta").setAttribute("aria-busy", String(valor));
  if (!valor) seleccionar("#atras")?.toggleAttribute("disabled", !puedeRetroceder());
}

/** Muestra un error sin borrar la pregunta ni las respuestas ya aceptadas. */
function mostrarError(error) {
  seleccionar("#mensaje-error").textContent = error.message;
  seleccionar("#error").hidden = false;
}

/** Envía una propuesta completa; solo sustituye el estado si el servidor la acepta. */
async function enviar(propuesta) {
  if (ocupado) return;
  establecerCarga(true); seleccionar("#error").hidden = true;
  try {
    const meta = propuesta.objetivo === undefined ? objetivo : propuesta.objetivo;
    const nuevo = await solicitar("/api/consultar", {hechos: propuesta.hechos, cierre: propuesta.cierre, continuar: propuesta.continuar, objetivo: meta});
    ({hechos, historial, cierre, continuar} = propuesta); objetivo = meta; resultado = nuevo;
    presentar();
  } catch (error) { mostrarError(error); } finally { establecerCarga(false); }
}

/** Empieza una consulta nueva sin conservar nada anterior. */
function iniciarConsulta(meta = null) {
  if (ocupado) return;
  objetivo = meta;
  hechos = {}; historial = []; cierre = {descartadas: [], final: null}; continuar = false; resultado = null; avance = 0;
  seleccionar("#bienvenida").hidden = true; seleccionar("#consulta").hidden = false;
  seleccionar("#resultado").hidden = true; seleccionar("#zona-pregunta").hidden = false;
  for (const id of ["#historial", "#detalle"]) { seleccionar(id).hidden = true; seleccionar(id).open = false; }
  seleccionar("#tarjeta-pregunta").innerHTML = '<p class="texto-secundario">Preparando tu consulta…</p>';
  window.scrollTo({top: 0});
  enviar({hechos: {}, historial: [], cierre, continuar: false, objetivo: meta});
}

/** Registra una respuesta nueva o una corrección. */
function responder(identificador, valor) {
  const nuevoHistorial = identificador in hechos ? historial : [...historial, identificador];
  const enConflicto = resultado?.conflictos.some(conflicto => conflicto.hechos.includes(identificador));
  enviar({hechos: {...hechos, [identificador]: valor}, historial: nuevoHistorial, cierre: {...cierre, final: null}, continuar: enConflicto ? false : continuar});
}

/** Responde a la confirmación final: Sí cierra, No descarta la conclusión, No sé la deja como indicio. */
function confirmar(valor) {
  const principal = resultado.principal;
  const nuevo = valor === "F" ? {descartadas: [...cierre.descartadas, principal.id], final: null} : {...cierre, final: valor};
  enviar({hechos, historial, cierre: nuevo, continuar});
}

function puedeRetroceder() { return historial.length > 0 || cierre.descartadas.length > 0 || cierre.final !== null; }

/** Deshace el último paso: la confirmación, una conclusión descartada o la última respuesta. */
function retroceder() {
  if (ocupado || !puedeRetroceder()) return;
  if (cierre.final !== null) return enviar({hechos, historial, cierre: {...cierre, final: null}, continuar});
  if (resultado.fase === "confirmacion" && cierre.descartadas.length) return enviar({hechos, historial, cierre: {...cierre, descartadas: cierre.descartadas.slice(0, -1)}, continuar});
  const ultimo = historial[historial.length - 1], {[ultimo]: _quitada, ...resto} = hechos;
  enviar({hechos: resto, historial: historial.slice(0, -1), cierre: {...cierre, final: null}, continuar: false});
}

/** Elige la mascota: lechuga para preguntas de plantas, pez para lo demás. */
function mascota(especie, expresion, extra = "late") {
  return `<div class="mascota ${especie} ${expresion} ${extra}" aria-hidden="true"></div>`;
}

function botones(valores = ["V", "F", "D"]) {
  const rotulos = {V: ["Sí", "S"], F: ["No", "N"], D: ["No sé", "D"]};
  return `<div class="respuestas">${valores.map(valor => `<button type="button" data-respuesta="${valor}" class="${valor === "D" ? "nsnc" : ""}">${rotulos[valor][0]}<kbd>${rotulos[valor][1]}</kbd></button>`).join("")}</div>`;
}

/** Explica qué preguntas se omitieron porque otra respuesta las vuelve imposibles (restricciones K1-K5). */
function nota_deducidas() {
  const deducidas = resultado.deducidas || [];
  if (!deducidas.length) return;
  const porCausa = new Map();
  for (const d of deducidas) porCausa.set(d.por, [...(porCausa.get(d.por) || []), d]);
  const partes = [...porCausa.values()].map(lista => `Como respondiste «No» a «${lista[0].por_texto}», no pregunto: ${lista.map(d => `«${d.texto}»`).join(", ")}.`);
  const nota = document.createElement("p");
  nota.className = "deducidas";
  nota.textContent = `Omití ${deducidas.length === 1 ? "una pregunta" : deducidas.length + " preguntas"} que ya no tienen sentido. ${partes.join(" ")}`;
  seleccionar("#tarjeta-pregunta").append(nota);
}

/** Pinta la pregunta activa; todas se contestan con Sí, No o Desconozco. */
function presentarPregunta() {
  const pregunta = resultado.pregunta, grupo = GRUPOS[pregunta.grupo];
  const etiqueta = pregunta.es_medicion ? `${pregunta.parametro_nombre}` : grupo.nombre;
  const pasos = pregunta.es_medicion && pregunta.escalones > 1
    ? `<p class="paso-medicion">${Array.from({length: pregunta.escalones}, (_, i) => `<i class="${i < pregunta.escalon ? "hecho" : ""}"></i>`).join("")} Medición · paso ${pregunta.escalon} de ${pregunta.escalones}</p>` : "";
  seleccionar("#tarjeta-pregunta").innerHTML = `<span class="etiqueta-pregunta">${icono(grupo.icono)} ${escapar(etiqueta)}${resultado.distintiva ? " · para distinguir otra posibilidad" : ""}</span>${objetivo ? `<p class="contexto">Estoy comprobando: ${escapar(titulos_meta())}</p>` : ""}${pregunta.contexto ? `<p class="contexto">${escapar(pregunta.contexto)}</p>` : ""}<h2 id="texto-pregunta">${escapar(pregunta.texto)}</h2>${pasos}${botones()}<details class="ayuda"><summary>¿Cómo puedo comprobarlo?</summary><p>${escapar(pregunta.ayuda)}</p></details><div class="acciones-pregunta"><button id="atras" type="button" class="boton-texto">← Atrás</button><span class="texto-secundario">Atajos: S, N, D</span></div>`;
  nota_deducidas();
  seleccionar("#atras").disabled = !puedeRetroceder();
  const especie = pregunta.grupo === "plantas" ? "lechuga" : "pez";
  seleccionar("#mascota-consulta").className = `mascota ${especie} pensando late`;
  seleccionar("#titulo-acompanante").textContent = resultado.distintiva ? "Una última duda." : "Vamos paso a paso.";
}

/** Título de la sospecha que se está comprobando. */
function titulos_meta() {
  const partida = guia.partidas.find(p => p.meta === objetivo);
  return partida ? partida.texto : (conclusiones[objetivo] || recomendaciones[objetivo]).titulo;
}

/** Veredicto de una sospecha: se cumple, no se cumple o falta información; ofrece seguir con la revisión completa. */
function presentarMeta() {
  const meta = resultado.meta, acciones = resultado.resultados.filter(r => r.tipo === "Verificación");
  const titulo = {V: "Sí, se cumple.", F: "No, no se cumple.", D: "Todavía no puedo confirmarlo."}[meta.estado];
  const sinSaber = meta.sin_saber.length ? `<p class="texto-secundario">Dijiste «Desconozco» a:</p><ul class="pendiente-lista">${meta.sin_saber.map(t => `<li>${escapar(t)}</li>`).join("")}</ul>` : "";
  seleccionar("#resultado").innerHTML = `<div class="cabecera-resultado">${mascota("pez", meta.estado === "V" ? "preocupado" : meta.estado === "F" ? "feliz" : "pensando")}<div><p class="antetitulo">Tu sospecha: ${escapar(titulos_meta())}</p><h1>${titulo}</h1><div class="veredicto-meta ${meta.estado === "V" ? "" : "no"}"><strong>${escapar(meta.titulo)}</strong><p>${escapar(meta.descripcion)}</p><p>${escapar(meta.mensaje)}</p></div>${sinSaber}</div></div>
    ${acciones.length ? `<section class="seccion"><h2>${icono("lista")} Qué hacer, en este orden</h2><div class="acciones-lista">${acciones.map(tarjetaAccion).join("")}</div></section>` : ""}
    <div class="acciones-resultado"><button id="revisar-todo" class="boton-principal" type="button">Revisar todo mi sistema →</button><button id="nueva-consulta" class="boton-suave" type="button">${icono("reiniciar")} Nueva consulta</button></div>
    <p class="alcance">${escapar(resultado.nota)} Es una guía educativa: no confirma enfermedades ni prescribe tratamientos.</p>`;
  seleccionar("#revisar-todo").addEventListener("click", () => enviar({hechos, historial, cierre, continuar, objetivo: null}));
  seleccionar("#nueva-consulta").addEventListener("click", reiniciar);
}

/** Muestra las respuestas que no cuadran con botones para corregirlas allí mismo. */
function presentarConflicto() {
  const filas = resultado.conflictos.map(conflicto => `<p>${escapar(conflicto.mensaje)}</p>${conflicto.hechos.map(identificador => `<div class="hecho-conflicto"><span>${escapar(preguntas[identificador].texto)}</span><div class="segmento" role="group" aria-label="Cambiar respuesta">${["V", "F", "D"].map(valor => `<button type="button" class="${hechos[identificador] === valor ? "activo" : ""}" data-cambiar="${identificador}" data-valor="${valor}">${formatearValor(valor)}</button>`).join("")}</div></div>`).join("")}`).join("");
  seleccionar("#tarjeta-pregunta").innerHTML = `<div class="conflicto"><span class="etiqueta-pregunta">${icono("alerta")} Algo no cuadra</span><h2>Espera, estas respuestas se contradicen.</h2>${filas}<div class="acciones-pregunta"><button id="atras" type="button" class="boton-texto">← Atrás</button><button id="continuar" type="button" class="boton-suave">Continuar sin esos datos</button></div></div>`;
  seleccionar("#mascota-consulta").className = "mascota pez sorprendido late";
  seleccionar("#titulo-acompanante").textContent = "Un momento…";
  seleccionar("#continuar").addEventListener("click", () => enviar({hechos, historial, cierre, continuar: true}));
}

/** Pregunta final tipo Akinator: ¿la conclusión coincide con lo que observas? */
function presentarConfirmacion() {
  const principal = resultado.principal, elemento = resultado.resultados.find(r => r.id === principal.id);
  const titulo = (conclusiones[principal.id] || recomendaciones[principal.id])?.titulo || principal.descripcion;
  const rondas = Array.from({length: cierre.maximo ?? resultado.cierre.maximo}, (_, i) => `<i class="${i < resultado.cierre.ronda - 1 ? "pasada" : i === resultado.cierre.ronda - 1 ? "activa" : ""}"></i>`).join("");
  const evidencias = (elemento?.respuestas || []).map(r => `<li>${escapar(r.pregunta)} <strong>${formatearValor(r.valor)}</strong></li>`).join("");
  seleccionar("#tarjeta-pregunta").innerHTML = `<span class="etiqueta-pregunta">${icono("info")} Creo que ya lo tengo</span><div class="rondas" aria-label="Ronda ${resultado.cierre.ronda} de ${resultado.cierre.maximo}">${rondas}</div><div class="conclusion-principal"><span class="chip ${principal.sustento}" title="${escapar(SUSTENTO[principal.sustento])}">${principal.sustento}</span><h2>${escapar(titulo)}</h2><p>${escapar(principal.descripcion)}</p></div>${evidencias ? `<details class="ayuda"><summary>Lo que me llevó a pensar esto</summary><ul class="lista-evidencia">${evidencias}</ul></details>` : ""}<p class="pregunta-akinator">¿Esto coincide con lo que observas?</p>${botones()}<div class="acciones-pregunta"><button id="atras" type="button" class="boton-texto">← Atrás</button><span class="texto-secundario">Con «No» lo descarto y busco otra explicación.</span></div>`;
  seleccionar("#mascota-consulta").className = "mascota pez pensando late";
  seleccionar("#titulo-acompanante").textContent = "¿Voy bien?";
}

/** Panel lateral: lecturas asumidas, señales detectadas y calidad de la consulta. */
function presentarPanel() {
  const calidad = resultado.calidad, hay = Object.keys(hechos).length > 0;
  const nombres = {conocido: "", pendiente: "Sin medir", desconozco: "Desconozco"};
  const lecturas = resultado.lecturas.map(l => `<div class="lectura"><b>${escapar(l.nombre)}</b><span class="valor"><span class="punto ${l.nivel || (l.estado === "desconozco" ? "desconozco" : "")}"></span>${l.intervalo ? escapar(l.intervalo) : nombres[l.estado]}</span></div>`).join("");
  const senales = resultado.resultados.filter(r => r.id[0] === "C" && r.tipo !== "Contexto").map(r => `<span class="senal">${escapar(r.titulo)}</span>`).join("");
  seleccionar("#panel-sistema").innerHTML = `<h3>${icono("lista")} Tu sistema</h3>${lecturas}<h3 class="separado">Lo que voy detectando</h3>${senales ? `<div class="senales">${senales}</div>` : '<p class="texto-secundario">Todavía nada fuera de lo normal.</p>'}${hay ? `<h3 class="separado">Calidad de la consulta</h3><span class="insignia-calidad calidad-${calidad.nivel.replace(" ", "")}">${escapar(calidad.nivel)}</span><p class="nota-panel">${escapar(calidad.razones[0] || calidad.efecto)}</p>` : ""}`;
}

function presentarAvisos() {
  const avisos = resultado.avisos.filter(a => a.id !== "K7a" || resultado.fase !== "pregunta");
  seleccionar("#avisos").innerHTML = resultado.fase === "cerrada" ? "" : avisos.map(a => `<div class="aviso alerta" role="status">${icono("alerta")}<p><strong>${a.id === "K8" ? "Parece que respondiste todo igual." : "Ojo."}</strong> ${escapar(a.mensaje)}</p></div>`).join("");
}

/** Sustituye identificadores técnicos (Q25 = F) por la pregunta correspondiente. */
function legible(texto) {
  return texto.replace(/(Q\d+[a-c]?) = ([VF])/g, (_, id, valor) => preguntas[id] ? `«${preguntas[id].texto}» se responda ${valor === "V" ? "Sí" : "No"}` : `${id} = ${valor}`);
}

function tarjetaAccion(elemento, indice) {
  const u = urgencia(elemento.prioridad);
  const motivos = elemento.motivos.map(m => `<div class="motivo"><p><strong>${escapar(m.regla)}</strong> · ${escapar(m.explicacion)}</p><p class="texto-secundario">${m.fuentes.map(f => `<span class="chip">${escapar(f)}</span>`).join("")}${escapar(m.cita)}${m.inferencia ? ' <span class="chip inferencia">inferencia propuesta</span>' : ""}</p></div>`).join("");
  const respuestas = elemento.respuestas.length ? `<p class="texto-secundario">Lo que me contaste:</p><ul class="lista-evidencia">${elemento.respuestas.map(r => `<li>${escapar(r.pregunta)} <strong>${formatearValor(r.valor)}</strong></li>`).join("")}</ul>` : "";
  return `<article class="accion ${u.clase === "u1" ? "urgente" : ""}"><div class="orden">${indice + 1}</div><div><h3>${escapar(elemento.titulo)}<span class="urgencia ${u.clase}">${u.texto}</span></h3><p>${escapar(sinTitulo(elemento))}</p>${(elemento.pasos || []).length ? `<p class="subtitulo-pasos">Qué puedes hacer</p><ul class="pasos">${elemento.pasos.map(p => `<li>${escapar(p)}</li>`).join("")}</ul>` : ""}<p class="verificacion">${icono("ok")}<span><strong>Sabrás que funcionó si:</strong> ${escapar(legible(elemento.verificacion))}</span></p><details><summary>¿Por qué lo sugerimos?</summary>${respuestas}${motivos}</details></div></article>`;
}

/** Pantalla final: veredicto, calidad, acciones por prioridad, posibles causas y datos pendientes. */
function presentarResultado() {
  const resumen = resultado.resumen, acciones = resultado.resultados.filter(r => r.tipo === "Verificación");
  const causas = resultado.resultados.filter(r => r.id[0] === "C" && r.tipo !== "Condición");
  const condiciones = resultado.resultados.filter(r => r.id[0] === "C" && r.tipo === "Condición");
  const urgente = acciones.some(a => a.prioridad <= 5);
  const titulos = {
    confirmada: resumen.valida ? "Esto es lo que te recomiendo." : "Tengo una respuesta, con reservas.", indicio: "Lo dejo como indicio.",
    inconclusa: "No logré dar con la causa.", insuficiente: "Necesito más información.", sin_regla: "No encontré nada que revisar.",
  };
  const expresion = {confirmada: resumen.valida ? "guino" : "pensando", indicio: "pensando", inconclusa: "triste", insuficiente: "pensando", sin_regla: "feliz"}[resumen.resultado];
  const especie = resultado.principal?.id && (conclusiones[resultado.principal.id]?.grupo === "plantas" || recomendaciones[resultado.principal.id]?.grupo === "plantas") ? "lechuga" : "pez";
  const nivel = resultado.calidad.nivel;
  const razones = [...resumen.razones].filter((r, i, todas) => todas.indexOf(r) === i);
  const faltantes = resultado.pendientes.filter(id => hechos[id] === "D").slice(0, 6);
  seleccionar("#resultado").innerHTML = `<div class="cabecera-resultado">${mascota(especie, urgente && resumen.resultado === "confirmada" ? "preocupado" : expresion)}<div><p class="antetitulo">Tu consulta</p><h1>${titulos[resumen.resultado]}</h1><p>${escapar(resumen.mensaje)}</p><div class="veredicto"><span class="insignia-calidad calidad-${nivel.replace(" ", "")}">${icono(nivel === "Confiable" ? "ok" : "info")} Calidad: ${escapar(nivel)}</span>${resumen.valida ? '<span class="chip Observada">Respuesta válida</span>' : ""}</div>${razones.length ? `<ul class="lista-evidencia">${razones.map(r => `<li>${escapar(r)}</li>`).join("")}</ul>` : ""}</div></div>
    ${acciones.length ? `<section class="seccion"><h2>${icono("lista")} Qué hacer, en este orden</h2><div class="acciones-lista">${acciones.map(tarjetaAccion).join("")}</div></section>` : ""}
    ${causas.length ? `<section class="seccion"><h2>${icono("info")} Posibles causas</h2><div class="causas">${causas.map(c => `<article class="causa"><span class="chip ${c.sustento}" title="${escapar(SUSTENTO[c.sustento])}">${c.sustento}</span><h3>${escapar(c.titulo)}</h3><p>${escapar(c.descripcion)}</p></article>`).join("")}</div></section>` : ""}
    <section class="seccion"><h2>${icono("agua")} Lo que mediste</h2><div class="lecturas-resumen">${resultado.lecturas.map(l => `<div class="lectura-tarjeta"><small>${escapar(l.nombre)}</small><strong><span class="punto ${l.nivel || (l.estado === "desconozco" ? "desconozco" : "")}"></span>${l.intervalo ? escapar(l.intervalo) : l.estado === "desconozco" ? "Desconozco" : "Sin medir"}</strong></div>`).join("")}</div></section>
    ${condiciones.length ? `<details class="desplegable"><summary>Condiciones que detecté</summary>${condiciones.map(c => `<p class="texto-secundario"><strong>${escapar(c.titulo)}.</strong> ${escapar(c.descripcion)}</p>`).join("")}</details>` : ""}
    ${faltantes.length ? `<section class="seccion"><h2>${icono("alerta")} Datos que me faltaron</h2><p class="texto-secundario">Si los consigues, la respuesta puede cambiar:</p><ul class="pendiente-lista">${faltantes.map(id => `<li>${escapar(preguntas[id].texto)}</li>`).join("")}</ul></section>` : ""}
    <div class="acciones-resultado"><button id="nueva-consulta" class="boton-principal" type="button">${icono("reiniciar")} Nueva consulta</button><button id="imprimir" class="boton-suave" type="button">${icono("imprimir")} Imprimir o guardar PDF</button><button id="guardar" class="boton-suave" type="button">${icono("descargar")} Descargar datos (JSON)</button></div>
    <p class="alcance">${escapar(resultado.nota)} Es una guía educativa: no confirma enfermedades ni prescribe tratamientos.</p>`;
  seleccionar("#nueva-consulta").addEventListener("click", reiniciar);
  seleccionar("#imprimir").addEventListener("click", () => { document.querySelectorAll("details").forEach(d => { d.open = true; }); window.print(); });
  seleccionar("#guardar").addEventListener("click", () => descargarInforme({fecha: new Date().toISOString(), hechos, calidad: resultado.calidad, resumen, principal: resultado.principal,
    resultados: resultado.resultados.map(r => ({id: r.id, titulo: r.titulo, sustento: r.sustento, prioridad: r.prioridad, reglas: r.justificaciones})), traza: resultado.traza}));
}

/** Historial editable con tres opciones por respuesta. */
function presentarHistorial() {
  seleccionar("#historial").hidden = !historial.length;
  seleccionar("#lista-respuestas").innerHTML = historial.map(identificador => `<div class="fila-respuesta"><span>${escapar(preguntas[identificador].texto)}</span><div class="segmento" role="group" aria-label="Respuesta">${["V", "F", "D"].map(valor => `<button type="button" class="${hechos[identificador] === valor ? "activo" : ""}" data-cambiar="${identificador}" data-valor="${valor}">${formatearValor(valor)}</button>`).join("")}</div></div>`).join("");
}

/** Detalle técnico plegado, separado de la recomendación práctica. */
function presentarDetalle() {
  const fuentes = base.fuentes.map(f => `<p class="texto-secundario"><span class="chip">${f.id}</span>${escapar(f.referencia)}</p>`).join("");
  seleccionar("#contenido-detalle").innerHTML = `<p class="texto-secundario">Para cada consulta el servidor ejecuta encadenamiento hacia adelante (reúne todo lo que se deduce) y hacia atrás (comprueba una meta y pregunta solo lo necesario) sobre la misma base de ${base.reglas.length} reglas.</p>${pintarTraza(resultado.traza)}<h3>Fuentes</h3>${fuentes}`;
}

/** Actualiza todos los paneles según la fase que devuelve el servidor. */
function presentar() {
  const fase = resultado.fase, cerrada = fase === "cerrada" || fase === "meta";
  seleccionar("#zona-pregunta").hidden = cerrada;
  seleccionar("#resultado").hidden = !cerrada;
  seleccionar("#detalle").hidden = !cerrada;
  seleccionar("#progreso").hidden = cerrada;
  if (fase === "pregunta") presentarPregunta();
  else if (fase === "conflicto") presentarConflicto();
  else if (fase === "confirmacion") presentarConfirmacion();
  else if (fase === "meta") presentarMeta();
  else presentarResultado();
  const {respondidas, restantes} = resultado.progreso, total = respondidas + restantes + (fase === "confirmacion" ? 0 : 0);
  avance = Math.max(avance, total ? respondidas / total : 0);
  seleccionar("#relleno-progreso").style.width = `${Math.round((fase === "confirmacion" ? 0.96 : avance) * 100)}%`;
  seleccionar("#texto-progreso").textContent = fase === "confirmacion" ? "Casi listo" : `Pregunta ${respondidas + 1} de unas ${respondidas + Math.max(restantes, 1)}`;
  presentarPanel(); presentarAvisos(); presentarHistorial(); presentarDetalle();
  if (!cerrada) seleccionar("#tarjeta-pregunta").scrollIntoView({block: "nearest", behavior: "smooth"}); else window.scrollTo({top: 0});
}

/** Borra toda la consulta y devuelve al inicio. */
function reiniciar() {
  if (ocupado) return;
  hechos = {}; historial = []; cierre = {descartadas: [], final: null}; continuar = false; resultado = null; objetivo = null;
  seleccionar("#consulta").hidden = true; seleccionar("#bienvenida").hidden = false; seleccionar("#error").hidden = true;
  for (const id of ["#resultado", "#contenido-detalle", "#lista-respuestas", "#tarjeta-pregunta", "#avisos"]) seleccionar(id).replaceChildren();
  window.scrollTo({top: 0});
}

/** Atajos de teclado: S, N y D responden; ← o Retroceso deshacen. */
function manejarTecla(evento) {
  if (!resultado || ocupado || evento.ctrlKey || evento.metaKey || evento.altKey || ["INPUT", "SELECT", "TEXTAREA"].includes(evento.target.tagName)) return;
  const tecla = evento.key.toLowerCase();
  const botonesRespuesta = seleccionar("#tarjeta-pregunta [data-respuesta]") ? ["V", "F", "D"] : null;
  if (botonesRespuesta && ["s", "1"].includes(tecla)) seleccionar('[data-respuesta="V"]').click();
  else if (botonesRespuesta && ["n", "2"].includes(tecla)) seleccionar('[data-respuesta="F"]').click();
  else if (botonesRespuesta && ["d", "3"].includes(tecla)) seleccionar('[data-respuesta="D"]').click();
  else if (["arrowleft", "backspace"].includes(tecla) && !seleccionar("#consulta").hidden) { evento.preventDefault(); retroceder(); }
}

/** Delegación de eventos para respuestas, correcciones y botones de la tarjeta. */
function manejarClic(evento) {
  const respuesta = evento.target.closest("[data-respuesta]");
  if (respuesta && resultado) {
    if (resultado.fase === "pregunta") responder(resultado.pregunta.id, respuesta.dataset.respuesta);
    else if (resultado.fase === "confirmacion") confirmar(respuesta.dataset.respuesta);
    return;
  }
  const tema = evento.target.closest("[data-tema-partida]");
  if (tema) return pintarPartidas(tema.dataset.temaPartida);
  const partida = evento.target.closest("[data-partida]");
  if (partida) return iniciarConsulta(partida.dataset.partida);
  const cambio = evento.target.closest("[data-cambiar]");
  if (cambio) responder(cambio.dataset.cambiar, cambio.dataset.valor);
  else if (evento.target.closest("#atras")) retroceder();
}

/** Pinta las áreas y, al elegir una, las sospechas desde las que se puede empezar. */
function pintarPartidas(tema = null) {
  seleccionar("#temas-partida").innerHTML = AREAS.map(([id, titulo]) => `<button type="button" class="tema-partida" data-tema-partida="${id}" aria-pressed="${id === tema}">${titulo}</button>`).join("");
  seleccionar("#lista-partidas").innerHTML = guia.partidas.filter(p => p.tema === tema).map(p => `<button type="button" class="partida" data-partida="${p.meta}">${escapar(p.texto)}</button>`).join("");
}

/** Carga el catálogo antes de habilitar la consulta. */
async function iniciar() {
  iniciarTema();
  seleccionar("#areas").innerHTML = AREAS.map(([id, titulo, texto]) => `<article class="area"><div class="icono-area">${icono(GRUPOS[id].icono)}</div><h3>${titulo}</h3><p>${texto}</p></article>`).join("");
  establecerCarga(true);
  try {
    base = await solicitar("/api/base");
    guia = await solicitar("/api/guia"); pintarPartidas();
    preguntas = Object.fromEntries(base.preguntas.map(p => [p.id, p]));
    conclusiones = Object.fromEntries(base.conclusiones.map(c => [c.id, c]));
    recomendaciones = Object.fromEntries(base.recomendaciones.map(r => [r.id, r]));
    seleccionar("#error").hidden = true;
  } catch (error) { mostrarError(error); } finally { establecerCarga(false); }
}
seleccionar("#iniciar-revision").addEventListener("click", () => iniciarConsulta());
seleccionar("#volver").addEventListener("click", reiniciar);
seleccionar("#reintentar").addEventListener("click", () => resultado ? enviar({hechos, historial, cierre, continuar}) : iniciar());
document.addEventListener("click", manejarClic);
document.addEventListener("keydown", manejarTecla);
iniciar();
