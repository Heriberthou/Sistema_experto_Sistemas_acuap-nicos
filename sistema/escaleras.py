"""Preguntas de rango y compuertas: habilitación y valores implícitos."""


def habilitada(base, hechos, identificador):
    """Una pregunta con padre solo se plantea si el padre tiene el valor que la habilita."""
    pregunta = next(p for p in base["preguntas"] if p["id"] == identificador)
    padre = pregunta.get("padre")
    return padre is None or hechos.get(padre) == pregunta["valor_padre"]


def completar(base, hechos):
    """Asigna el valor implícito a las preguntas no planteadas, del padre al hijo.

    F cuando la respuesta del padre excluye su intervalo; D cuando el padre es D,
    no tiene respuesta o la pregunta está habilitada pero sin responder.
    """
    completos = dict(hechos)
    for pregunta in base["preguntas"]:
        padre = pregunta.get("padre")
        if not padre or pregunta["id"] in completos:
            continue
        valor_padre = completos.get(padre, "D")
        completos[pregunta["id"]] = "F" if valor_padre in ("V", "F") and valor_padre != pregunta["valor_padre"] else "D"
    return completos
