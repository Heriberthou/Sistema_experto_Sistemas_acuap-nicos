"""Validación de entradas y restricciones K1-K12, independiente del motor."""
from .escaleras import completar
from .logica import evaluar

OBSERVACIONES_BLOQUE = [f"Q{numero:02d}" for numero in range(6, 20)]
UMBRAL_BLOQUE = 12
SUSPENDIDAS_POR_K7A = {"C12", "C16", "C17", "C20"}


def validar_hechos(base, hechos):
    """Rechaza identificadores o valores inválidos antes de inferir.

    Solo se aceptan las cadenas V, F y D; cualquier otra entrada no llega a la memoria.
    """
    if not isinstance(hechos, dict):
        raise ValueError("Los hechos deben ser un objeto JSON")
    conocidas = {pregunta["id"] for pregunta in base["preguntas"]}
    for identificador, valor in hechos.items():
        if identificador not in conocidas:
            raise ValueError(f"Pregunta desconocida: {identificador}")
        if not isinstance(valor, str) or valor not in ("V", "F", "D"):
            raise ValueError(f"{identificador}: responde Sí, No o Desconozco")


def _estado(arbol, hechos):
    """Evalúa un antecedente de restricción sobre los hechos actuales."""
    return evaluar(arbol, lambda identificador: (hechos.get(identificador, "D"), []))[0]


def revisar_consistencia(base, hechos):
    """Aplica K1-K12 y devuelve (hechos efectivos, violaciones, avisos).

    Las violaciones (K1-K5 y K9) tratan como D los hechos implicados, sin borrar
    las respuestas originales. Los avisos (K6, K7, K8) no cambian ningún hecho.
    Cada restricción se evalúa sobre el resultado de las anteriores, como en el documento.
    """
    seguros, violaciones, avisos = dict(hechos), [], []
    por_id = {restriccion["id"]: restriccion for restriccion in base["restricciones"]}
    for restriccion in base["restricciones"]:
        if restriccion["tipo"] == "contradiccion" and _estado(restriccion["si"], seguros) == "V":
            violaciones.append({"id": restriccion["id"], "mensaje": restriccion["mensaje"], "hechos": list(restriccion["anula"])})
            for identificador in restriccion["anula"]:
                seguros[identificador] = "D"
    for hijo, otro, valor in por_id["K9"]["pares"]:
        if seguros.get(hijo) == "V" and seguros.get(otro) == valor:
            violaciones.append({"id": "K9", "mensaje": por_id["K9"]["mensaje"], "hechos": [hijo, otro]})
            seguros[hijo] = seguros[otro] = "D"
    seguros = completar(base, seguros)
    for restriccion in base["restricciones"]:
        if restriccion["tipo"] in ("aviso", "evasion") and _estado(restriccion["si"], seguros) == "V":
            avisos.append({"id": restriccion["id"], "mensaje": restriccion["mensaje"]})
    iguales = [valor for valor in "VF" if sum(seguros.get(i, "D") == valor for i in OBSERVACIONES_BLOQUE) >= UMBRAL_BLOQUE]
    if iguales:
        avisos.append({"id": "K8", "mensaje": por_id["K8"]["mensaje"]})
    return seguros, violaciones, avisos


def hipotesis_suspendidas(avisos):
    """K7(a) suspende las hipótesis que dependen de mediciones que el usuario evitó."""
    return set(SUSPENDIDAS_POR_K7A) if any(aviso["id"] == "K7a" for aviso in avisos) else set()
