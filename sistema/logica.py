"""Evaluación compartida: lógica de Kleene fuerte con valores V, F y D."""


def negar(valor):
    """Intercambia verdadero/falso y conserva el valor desconocido."""
    return {"V": "F", "F": "V", "D": "D"}[valor]


def evaluar(nodo, resolver):
    """Devuelve estado, evidencia visitada y preguntas faltantes.

    ``resolver`` devuelve (valor, faltantes) para una pregunta o conclusión.
    Y/O usan cortocircuito de izquierda a derecha. La comparación explícita
    ``es = D`` vale V solo cuando la respuesta es Desconozco y nunca es un faltante.
    """
    if "q" in nodo or "c" in nodo:
        identificador = nodo.get("q", nodo.get("c"))
        valor, faltantes = resolver(identificador)
        esperado = nodo.get("es", "V")
        if esperado == "D":
            estado, faltantes = ("V" if valor == "D" else "F"), []
        elif valor == "D":
            estado = "D"
        else:
            estado = "V" if valor == esperado else "F"
        evidencia = [{"hecho": identificador, "valor": valor, "referencia": esperado, "estado": estado}]
        return estado, evidencia, list(faltantes) if estado == "D" else []
    if "no" in nodo:
        estado, evidencia, faltantes = evaluar(nodo["no"], resolver)
        return negar(estado), evidencia, faltantes
    es_conjuncion = "y" in nodo
    dominante = "F" if es_conjuncion else "V"
    neutro = "V" if es_conjuncion else "F"
    evidencias, pendientes = [], []
    hay_desconocidos = False
    for hijo in nodo["y" if es_conjuncion else "o"]:
        estado, evidencia, faltantes = evaluar(hijo, resolver)
        evidencias.extend(evidencia)
        pendientes.extend(identificador for identificador in faltantes if identificador not in pendientes)
        if estado == dominante:
            return dominante, evidencias, []
        hay_desconocidos = hay_desconocidos or estado == "D"
    return ("D" if hay_desconocidos else neutro), evidencias, pendientes


def simbolos(nodo):
    """Extrae los símbolos de un árbol lógico sin evaluarlo."""
    if "q" in nodo or "c" in nodo:
        return {nodo.get("q", nodo.get("c"))}
    if "no" in nodo:
        return simbolos(nodo["no"])
    return set().union(*(simbolos(hijo) for hijo in nodo.get("y", nodo.get("o", []))))
