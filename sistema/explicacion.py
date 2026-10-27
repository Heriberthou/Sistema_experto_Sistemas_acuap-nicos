"""Convierte las derivaciones en resultados ordenados y explicaciones legibles."""


def registrar_paso(regla, evidencias):
    """Guarda la evidencia ya evaluada sin disparar búsquedas adicionales."""
    return {"regla": regla["id"], "conclusion": regla["entonces"], "expresion": regla["expresion"],
            "explicacion": regla["explicacion"], "cita": regla["cita"], "fuentes": regla["fuentes"],
            "inferencia": regla["inferencia"], "evidencias": evidencias}


def reunir_resultados(base, memoria, pasos, sustento):
    """Conserva todas las justificaciones y ordena las recomendaciones por prioridad."""
    catalogo = base["conclusiones"] + base["recomendaciones"]
    return [{**elemento, **({"sustento": sustento[elemento["id"]]} if elemento["id"] in sustento else {}),
             "justificaciones": [paso["regla"] for paso in pasos if paso["conclusion"] == elemento["id"]]}
            for elemento in catalogo if memoria.get(elemento["id"]) == "V"]


def explicar_resultado(identificador, pasos, preguntas, visitados=None):
    """Recorre la cadena de reglas hasta las observaciones y mediciones iniciales."""
    visitados = set() if visitados is None else visitados
    if identificador in visitados:
        return []
    visitados = visitados | {identificador}
    respuestas = []
    for paso in pasos:
        if paso["conclusion"] != identificador:
            continue
        for evidencia in paso["evidencias"]:
            hecho = evidencia["hecho"]
            if hecho in preguntas:
                if evidencia["valor"] == "D" and evidencia["referencia"] != "D":
                    continue
                respuesta = {"id": hecho, "pregunta": preguntas[hecho]["texto"], "valor": evidencia["valor"],
                             "parametro": preguntas[hecho].get("parametro")}
                if respuesta not in respuestas:
                    respuestas.append(respuesta)
            elif evidencia["valor"] == "V":
                for respuesta in explicar_resultado(hecho, pasos, preguntas, visitados):
                    if respuesta not in respuestas:
                        respuestas.append(respuesta)
    return respuestas


def lecturas(base, hechos, seguros):
    """Intervalo asumido de cada medición, para mostrarlo sin que se teclee ningún número."""
    salida = []
    for parametro in base["parametros"]:
        intervalo = next((i for i in parametro["intervalos"] if all(seguros.get(q) == v for q, v in i["cuando"].items())), None)
        if intervalo:
            estado = "conocido"
        elif any(hechos.get(q) == "D" for q in parametro["escalera"]):
            estado = "desconozco"
        else:
            estado = "pendiente"
        salida.append({"id": parametro["id"], "nombre": parametro["nombre"], "unidad": parametro["unidad"], "estado": estado,
                       "intervalo": intervalo["texto"] if intervalo else None, "nivel": intervalo["nivel"] if intervalo else None})
    return salida
