"""Orquesta la consulta adaptativa: elige la siguiente pregunta, valida y cierra como Akinator."""
from collections import Counter

from .escaleras import habilitada
from .explicacion import explicar_resultado, lecturas, reunir_resultados
from .logica import evaluar, simbolos
from .motor import EncadenamientoAtras, adelante, filtrar_por_calidad, preparar
from .calidad import calcular_sustento

MAXIMO_RONDAS = 3
SEGURIDAD = ("Q06", "Q07", "Q09")
PRIMER_ESCALON = ("Q01a", "Q02a", "Q03a", "Q04a", "Q05a")


def puntuar(base, hechos, seguros, memoria, bloqueadas):
    """Cuenta en cuántas reglas o restricciones pendientes interviene cada hecho sin responder (sección 6.6)."""
    busqueda = EncadenamientoAtras(base, seguros, bloqueadas)
    cuenta = Counter()
    for regla in base["reglas"]:
        if memoria.get(regla["entonces"]) == "V" or regla["entonces"] in bloqueadas:
            continue
        estado, _, faltantes = evaluar(regla["si"], busqueda.demostrar)
        if estado == "D":
            cuenta.update(set(faltantes))
    for restriccion in base["restricciones"]:
        if restriccion.get("si"):
            cuenta.update(q for q in simbolos(restriccion["si"]) if q not in hechos)
    # Una compuerta sin reglas propias hereda el interés de la pregunta más relevante que habilita.
    for pregunta in reversed(base["preguntas"]):
        if pregunta.get("padre") and pregunta["id"] not in hechos:
            cuenta[pregunta["padre"]] = max(cuenta[pregunta["padre"]], cuenta[pregunta["id"]])
    return cuenta


def elegir_pregunta(base, hechos, cuenta):
    """Entre las preguntas habilitadas y sin responder, la que aparece en más reglas pendientes."""
    candidatas = [p for p in base["preguntas"] if p["id"] not in hechos and habilitada(base, hechos, p["id"])
                  and cuenta[p["id"]] > 0 and p.get("despues_de", "") in hechos | {"": 0}]
    orden = {p["id"]: i for i, p in enumerate(base["preguntas"])}

    def clave(pregunta):
        """Más reglas primero; en empate, seguridad, primer escalón y orden del catálogo."""
        identificador = pregunta["id"]
        grupo = 0 if identificador in SEGURIDAD else 1 if identificador in PRIMER_ESCALON else 2
        return (-cuenta[identificador], grupo, orden[identificador])

    candidatas.sort(key=clave)
    return candidatas


def describir_pregunta(base, pregunta, hechos):
    """Prepara los datos que la interfaz necesita para mostrar una pregunta."""
    parametro = next((p for p in base["parametros"] if pregunta["id"] in p["escalera"]), None)
    salida = {**pregunta, "es_medicion": parametro is not None}
    if parametro:
        salida.update(parametro_nombre=parametro["nombre"], unidad=parametro["unidad"],
                      escalon=parametro["escalera"].index(pregunta["id"]) + 1, escalones=len(parametro["escalera"]))
    padre = pregunta.get("padre")
    if padre:
        texto_padre = next(p["texto"] for p in base["preguntas"] if p["id"] == padre)
        salida["contexto"] = f"Respondiste «{'Sí' if hechos.get(padre) == 'V' else 'No'}» a: {texto_padre}"
    return salida


def conclusion_principal(base, resultados, pasos, sustento):
    """La conclusión que respalda la recomendación más urgente; si no hay, la propia recomendación."""
    acciones = [r for r in resultados if r["id"][0] == "A"]
    if not acciones:
        return None
    accion = acciones[0]
    paso = next(p for p in pasos if p["conclusion"] == accion["id"])
    derivadas = [e["hecho"] for e in paso["evidencias"] if e["hecho"][0] == "C" and e["valor"] == "V"]
    catalogo = {c["id"]: c for c in base["conclusiones"]}
    if derivadas:
        elemento = catalogo[derivadas[-1]]
        return {"id": elemento["id"], "tipo": "conclusion", "descripcion": elemento["descripcion"],
                "sustento": sustento[elemento["id"]], "accion": accion["id"]}
    return {"id": accion["id"], "tipo": "accion", "descripcion": accion["descripcion"], "sustento": "Observada", "accion": accion["id"]}


def alternativa_pendiente(base, hechos, seguros, memoria, bloqueadas):
    """La conclusión aún no sustentada con menos hechos faltantes y una pregunta que la distinga."""
    busqueda = EncadenamientoAtras(base, seguros, bloqueadas)
    opciones = []
    for conclusion in base["conclusiones"]:
        if conclusion["id"] in bloqueadas or memoria.get(conclusion["id"]) == "V":
            continue
        estado, faltantes = busqueda.demostrar(conclusion["id"])
        pregunta = next((q for q in faltantes if q not in hechos and habilitada(base, hechos, q)), None)
        if estado == "D" and faltantes:
            opciones.append((len(faltantes), conclusion, faltantes, pregunta))
    opciones.sort(key=lambda opcion: (opcion[0], opcion[1]["id"]))
    return opciones[0] if opciones else None


def deducir_descartadas(base, hechos):
    """Preguntas que ya no tienen sentido: si el antecedente de una restricción K1-K5 ya se cumple en
    su primera parte, el resto no puede ser verdad y se asume No sin preguntarlo (por ejemplo, sin
    electricidad el aireador y la bomba no pueden estar encendidos). Se repite hasta que no cambie nada."""
    textos = {p["id"]: p["texto"] for p in base["preguntas"]}
    efectivos, deducidas = dict(hechos), []
    cambio = True
    while cambio:
        cambio = False
        for restriccion in base["restricciones"]:
            partes = (restriccion.get("si") or {}).get("y", [])
            if restriccion["tipo"] != "contradiccion" or len(partes) != 2:
                continue
            causa, resto = partes
            if "q" not in causa or efectivos.get(causa["q"]) != causa["es"]:
                continue
            for literal in (resto["o"] if "o" in resto else [resto]):
                pregunta = literal.get("q")
                if literal.get("es") == "V" and pregunta and pregunta not in efectivos:
                    efectivos[pregunta] = "F"
                    deducidas.append({"id": pregunta, "texto": textos[pregunta], "valor": "F", "por": causa["q"],
                                      "por_texto": textos[causa["q"]], "restriccion": restriccion["id"]})
                    cambio = True
    origen = {d["id"]: d for d in deducidas}
    for d in deducidas:  # la causa que se muestra es siempre una respuesta del usuario, no otra deducción
        while d["por"] in origen:
            d["por"], d["por_texto"] = origen[d["por"]]["por"], origen[d["por"]]["por_texto"]
    return efectivos, deducidas


def consultar(base, hechos, cierre=None, continuar=False):
    """Deriva resultados, valida y decide si pregunta, pide confirmación o cierra la consulta."""
    cierre = cierre or {}
    descartadas = list(dict.fromkeys(cierre.get("descartadas", [])))
    final = cierre.get("final")
    if final not in (None, "V", "F", "D") or not isinstance(descartadas, list):
        raise ValueError("Cierre inválido")
    salidas = {e["id"] for e in base["conclusiones"] + base["recomendaciones"]}
    if set(descartadas) - salidas:
        raise ValueError("Conclusión descartada desconocida")
    original = hechos
    hechos, deducidas = deducir_descartadas(base, original)
    seguros, violaciones, avisos, bloqueadas, calidad = preparar(base, hechos, descartadas)
    sustento = calcular_sustento(base)
    memoria, pasos = adelante(base, seguros, bloqueadas)
    preguntas = {p["id"]: p for p in base["preguntas"]}
    resultados = filtrar_por_calidad(reunir_resultados(base, memoria, pasos, sustento), calidad)
    for resultado in resultados:
        resultado["respuestas"] = explicar_resultado(resultado["id"], pasos, preguntas)
        resultado["motivos"] = [{"regla": p["regla"], "explicacion": p["explicacion"], "cita": p["cita"], "fuentes": p["fuentes"],
                                 "inferencia": p["inferencia"]} for p in pasos if p["conclusion"] == resultado["id"]]
    cuenta = puntuar(base, hechos, seguros, memoria, bloqueadas)
    candidatas = elegir_pregunta(base, hechos, cuenta)
    esperando_correccion = bool(violaciones) and not continuar
    principal = conclusion_principal(base, resultados, pasos, sustento)
    alternativa = None
    pregunta, distintiva = (candidatas[0], False) if candidatas and not esperando_correccion else (None, False)
    if pregunta is None and not esperando_correccion and not principal and descartadas and len(descartadas) < MAXIMO_RONDAS:
        alternativa = alternativa_pendiente(base, hechos, seguros, memoria, bloqueadas)
        if alternativa and alternativa[3]:
            pregunta, distintiva = preguntas[alternativa[3]], True
    # Fase de la consulta
    if esperando_correccion:
        fase = "conflicto"
    elif pregunta is not None:
        fase = "pregunta"
    elif final in ("V", "D") or len(descartadas) >= MAXIMO_RONDAS or principal is None:
        fase = "cerrada"
    else:
        fase = "confirmacion"
    resumen = None
    if fase == "cerrada":
        resumen = cerrar(base, hechos, resultados, principal, calidad, final, descartadas, alternativa, pasos)
    pendientes = []
    busqueda = EncadenamientoAtras(base, seguros, bloqueadas)
    for identificador in sorted(salidas):
        _, faltantes = busqueda.demostrar(identificador)
        pendientes.extend(h for h in faltantes if h not in pendientes)
    respondidas = len(original)
    return {"fase": fase, "hechos": original, "deducidas": deducidas, "pregunta": describir_pregunta(base, pregunta, hechos) if pregunta else None,
            "distintiva": distintiva, "conflictos": violaciones, "avisos": avisos, "calidad": calidad,
            "lecturas": lecturas(base, hechos, seguros), "resultados": resultados, "traza": pasos,
            "principal": principal if fase in ("confirmacion", "cerrada") else None, "resumen": resumen,
            "cierre": {"descartadas": descartadas, "ronda": len(descartadas) + 1, "maximo": MAXIMO_RONDAS, "final": final},
            "pendientes": pendientes, "progreso": {"respondidas": respondidas, "restantes": len(candidatas)},
            "reglas_atras": [p["regla"] for p in EncadenamientoAtras(base, seguros, bloqueadas).pasos],
            "nota": "La revisión se basa en los datos aportados y en las reglas disponibles; no descarta otros problemas."}


def cerrar(base, hechos, resultados, principal, calidad, final, descartadas, alternativa, pasos):
    """Mensaje final: una respuesta es válida si la calidad es Confiable y el sustento es Medida u Observada."""
    razones = []
    if calidad["nivel"] != "Confiable":
        razones.extend(calidad["razones"] or [calidad["efecto"]])
    if principal is None:
        if calidad["nivel"] == "Insuficiente":
            return {"resultado": "insuficiente", "valida": False, "razones": razones,
                    "mensaje": "No hay información suficiente para orientarte. Toma las mediciones que faltan y vuelve a intentarlo."}
        if len(descartadas) >= MAXIMO_RONDAS or descartadas:
            return {"resultado": "inconclusa", "valida": False, "razones": razones,
                    "mensaje": "Con lo que sabemos no encontré otra explicación. Consulta a una persona con experiencia en acuaponía.",
                    "alternativa": alternativa[1]["descripcion"] if alternativa else None}
        return {"resultado": "sin_regla", "valida": False, "razones": razones,
                "mensaje": "Ninguna regla aplica a tus respuestas. Esto no demuestra que el sistema esté libre de problemas."}
    if len(descartadas) >= MAXIMO_RONDAS and final is None:
        return {"resultado": "inconclusa", "valida": False, "razones": razones,
                "mensaje": "Llegamos al máximo de rondas sin una conclusión que coincida con lo que observas. Consulta a una persona con experiencia."}
    if principal["sustento"] == "Hipótesis":
        razones.append("La conclusión principal es una hipótesis (inferencia propuesta), no un hecho medido.")
    if final == "D":
        return {"resultado": "indicio", "valida": False, "razones": razones + ["Dijiste que no sabes si coincide: se conserva como indicio."],
                "mensaje": "Se conserva como indicio. Mide o confirma lo que falta antes de actuar."}
    valida = calidad["nivel"] == "Confiable" and principal["sustento"] in ("Medida", "Observada")
    return {"resultado": "confirmada", "valida": valida, "razones": razones,
            "mensaje": "Respuesta confirmada." if valida else "Respuesta confirmada, pero con reservas."}
