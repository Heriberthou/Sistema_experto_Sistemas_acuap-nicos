"""Ejecuta los casos de prueba del documento y compara lo esperado con lo obtenido."""
from .motor import ejecutar

NUMERO = lambda identificador: int(identificador[1:])


def hechos_del_caso(base, caso):
    """T4 responde Desconozco a todas las preguntas; los demás casos usan sus hechos."""
    return {pregunta["id"]: "D" for pregunta in base["preguntas"]} if caso.get("todo_d") else dict(caso["hechos"])


def evaluar_caso(base, caso):
    """Devuelve las diferencias entre lo esperado y lo obtenido; una lista vacía significa que el caso pasa."""
    hechos = hechos_del_caso(base, caso)
    if caso.get("error_esperado"):
        try:
            ejecutar(base, hechos)
        except ValueError as error:
            return {"id": caso["id"], "nombre": caso["nombre"], "ok": True, "diferencias": [], "obtenido": f"Entrada rechazada: {error}"}
        return {"id": caso["id"], "nombre": caso["nombre"], "ok": False, "diferencias": ["La entrada inválida no fue rechazada"], "obtenido": ""}
    adelante, atras = ejecutar(base, hechos, "adelante", caso["objetivo"]), ejecutar(base, hechos, "atras", caso["objetivo"])
    diferencias = []

    def comparar(campo, obtenido, esperado):
        """Registra una diferencia legible."""
        if obtenido != esperado:
            diferencias.append(f"{campo}: esperado {esperado}, obtenido {obtenido}")

    ordenadas = lambda ids: sorted(ids, key=lambda i: (i[0], NUMERO(i)))
    ids = ordenadas(r["id"] for r in adelante["resultados"])
    acciones = [r["id"] for r in adelante["resultados"] if r["id"][0] == "A"]
    if not caso.get("solo_atras"):
        comparar("conclusiones y acciones", ids, ordenadas(caso["esperados"]))
        if caso["id"] != "T20" and "reglas_esperadas" in caso:
            comparar("reglas", sorted(adelante["reglas_activadas"], key=NUMERO), caso["reglas_esperadas"])
        if "orden" in caso:
            comparar("orden de presentación", acciones, caso["orden"])
        if "calidad" in caso:
            comparar("calidad", adelante["calidad"]["nivel"], caso["calidad"])
        if "conflictos" in caso:
            comparar("restricciones violadas", [c["id"] for c in adelante["conflictos"]], caso["conflictos"])
        for aviso in caso.get("avisos", []):
            if aviso not in [a["id"] for a in adelante["avisos"]]:
                diferencias.append(f"falta el aviso {aviso}")
    if "estado_atras" in caso:
        comparar(f"{caso['objetivo']} hacia atrás", atras["objetivo"]["estado"], caso["estado_atras"])
    if "preguntas_atras" in caso:
        comparar("preguntas hacia atrás", sorted(atras["preguntas_consultadas"]), sorted(caso["preguntas_atras"]))
    if "reglas_atras" in caso:
        comparar("reglas hacia atrás", sorted(atras["reglas_activadas"]), sorted(caso["reglas_atras"]))
    if "faltantes_atras" in caso:
        comparar("faltantes hacia atrás", sorted(atras["objetivo"]["faltantes"]), sorted(caso["faltantes_atras"]))
    obtenido = (f"{', '.join(ids) or 'sin conclusiones'}. Reglas: {', '.join(sorted(adelante['reglas_activadas'], key=NUMERO)) or 'ninguna'}. "
                f"Calidad: {adelante['calidad']['nivel']}.")
    return {"id": caso["id"], "nombre": caso["nombre"], "ok": not diferencias, "diferencias": diferencias, "obtenido": obtenido}


def evaluar_todos(base, casos):
    """Ejecuta todos los casos; cada uno parte de una memoria nueva (T7)."""
    return [evaluar_caso(base, caso) for caso in casos]
