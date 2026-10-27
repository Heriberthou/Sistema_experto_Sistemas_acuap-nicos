"""Nivel de calidad de la consulta y nivel de sustento de cada conclusión."""
from .logica import simbolos

CLAVE = ("Q01a", "Q04a", "Q05a")


def nivel_calidad(hechos, seguros, violaciones, avisos):
    """Cuenta violaciones y avisos; no es una probabilidad (sección 4.6 del documento)."""
    ids = {aviso["id"] for aviso in avisos}
    razones = []
    if not any(valor in ("V", "F") for valor in hechos.values()):
        return {"nivel": "Insuficiente", "razones": ["Todavía no hay respuestas con información."],
                "efecto": "No hay datos suficientes para concluir."}
    if len(violaciones) >= 2 or "K8" in ids:
        if len(violaciones) >= 2:
            razones.append("Hay varias respuestas contradictorias.")
        if "K8" in ids:
            razones.append("Las respuestas siguen un patrón en bloque.")
        return {"nivel": "No fiable", "razones": razones,
                "efecto": "Solo se emiten las acciones de seguridad (A06 y A09); conviene repetir la consulta."}
    if violaciones:
        razones.append("Una respuesta contradice a otra y se trató como desconocida.")
    if "K6" in ids:
        razones.append("Hay valores extremos sin signos en los peces: posible error de lectura.")
    if "K7a" in ids or "K7b" in ids:
        razones.append("Se evitaron mediciones u observaciones que hacen falta.")
    signos = seguros.get("Q06") == "V" or seguros.get("Q07") == "V"
    if signos and any(seguros.get(i, "D") == "D" for i in CLAVE) and "K7a" not in ids:
        razones.append("Hay signos en los peces y faltan mediciones clave.")
    if razones:
        return {"nivel": "Parcial", "razones": razones,
                "efecto": "Las hipótesis se marcan como indicio y se piden los datos pendientes."}
    return {"nivel": "Confiable", "razones": [], "efecto": "Se emiten todas las conclusiones y recomendaciones."}


def calcular_sustento(base):
    """Medida, Observada o Hipótesis para cada conclusión, según su cadena de reglas."""
    medidas = {pregunta["id"] for pregunta in base["preguntas"] if "parametro" in pregunta}
    dependencias = {}
    for regla in base["reglas"]:
        dependencias.setdefault(regla["entonces"], set()).update(simbolos(regla["si"]))

    def usa_medicion(identificador, visitados=()):
        """Recorre la cadena hasta encontrar una respuesta de rango."""
        return any(s in medidas or (s[0] == "C" and s not in visitados and usa_medicion(s, visitados + (identificador,)))
                   for s in dependencias.get(identificador, ()))

    sustento = {}
    for conclusion in base["conclusiones"]:
        if conclusion["tipo"] == "Hipótesis":
            sustento[conclusion["id"]] = "Hipótesis"
        else:
            sustento[conclusion["id"]] = "Medida" if usa_medicion(conclusion["id"]) else "Observada"
    return sustento
