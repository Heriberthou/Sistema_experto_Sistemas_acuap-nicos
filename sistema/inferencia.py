"""Dos algoritmos propios sobre una misma base; memoria nueva por petición."""
from collections import Counter

from .conocimientos import dependencias
from .logica import disyuncion, evaluar

ESTADOS = {"V": "Sustentada", "F": "No sustentable con las respuestas conocidas", "D": "Indeterminada"}


def validar_hechos(base_conocimientos, hechos):
    """Rechaza respuestas cuyo identificador o valor no pertenece al vocabulario."""
    if not isinstance(hechos, dict):
        raise ValueError("Los hechos deben ser un objeto con identificadores Q y valores V/F/D")
    permitidos = {q["id"] for q in base_conocimientos["preguntas"]}
    if set(hechos) - permitidos:
        raise ValueError("Solo se admiten preguntas Q conocidas como hechos de entrada")
    if any(not isinstance(v, str) or v not in ("V", "F", "D") for v in hechos.values()):
        raise ValueError("Las respuestas deben ser V, F o D")


def consistencia(base_conocimientos, hechos):
    """Detecta respuestas incompatibles y bloquea únicamente los hechos afectados."""
    """Detecta contradicciones explícitas; no inventa respuestas por implicación."""
    conflictos, bloqueados, vistos = [], set(), set()
    for comprobar in base_conocimientos["consistencia"]:
        a, b = comprobar["si_hecho"], comprobar["entonces_hecho"]
        if hechos.get(a) == comprobar["si_valor"] and hechos.get(b, "D") not in ("D", comprobar["entonces_valor"]):
            pareja = tuple(sorted((a, b)))
            if pareja not in vistos:
                conflictos.append({"hechos": list(pareja), "message": f"{a}={comprobar['si_valor']} requiere {b}={comprobar['entonces_valor']}. Revise las respuestas de la misma muestra o período."})
                vistos.add(pareja)
            bloqueados.update(pareja)
    hechos_seguros = dict(hechos)
    for clave in bloqueados:
        hechos_seguros[clave] = "D"
    return hechos_seguros, conflictos, bloqueados


def traza(regla, resolver):
    """Construye la justificación de una regla con las premisas utilizadas."""
    return {"regla": regla["id"], "conclusion": regla["conclusion"],
            "expresion": regla["expresion"], "explicacion": regla["explicacion"],
            "fuentes": regla["fuentes"],
            "premisas": {clave: resolver(clave) for clave in sorted(dependencias(regla["condicion"]))}}


def adelante(base_conocimientos, hechos):
    """Deriva hechos hasta que ninguna regla pueda aportar una activación nueva."""
    memoria, activadas, pasos = dict(hechos), set(), []
    while True:
        hubo_cambios = False
        for regla in base_conocimientos["reglas"]:
            if regla["id"] in activadas:
                continue
            if evaluar(regla["condicion"], lambda clave: memoria.get(clave, "D")) == "V":
                pasos.append(traza(regla, lambda clave: memoria.get(clave, "D")))
                activadas.add(regla["id"])
                memoria[regla["conclusion"]] = "V"
                hubo_cambios = True
        if not hubo_cambios:
            break
    return memoria, pasos


class EncadenamientoAtras:
    """Búsqueda por metas. F es fracaso de prueba, nunca un hecho negativo nuevo."""
    def __init__(self, base_conocimientos, hechos):
        """Inicializa la búsqueda por metas con memoria independiente por consulta."""
        self.hechos = hechos
        self.preguntas = {q["id"] for q in base_conocimientos["preguntas"]}
        self.reglas = base_conocimientos["reglas"]
        self.cache_metas, self.activos, self.pasos, self.activadas = {}, set(), [], set()
        self.reglas_visitadas = []

    def demostrar(self, objetivo):
        """Intenta demostrar una meta a partir de hechos o de reglas alternativas."""
        if objetivo in self.preguntas:
            return self.hechos.get(objetivo, "D")
        if objetivo in self.cache_metas:
            return self.cache_metas[objetivo]
        if objetivo in self.activos:
            return "D"
        self.activos.add(objetivo)
        valores = []
        for regla in self.reglas:
            if regla["conclusion"] != objetivo:
                continue
            self.reglas_visitadas.append(regla["id"])
            valor = evaluar(regla["condicion"], self.demostrar)
            valores.append(valor)
            if valor == "V" and regla["id"] not in self.activadas:
                self.pasos.append(traza(regla, self.demostrar))
                self.activadas.add(regla["id"])
        self.activos.remove(objetivo)
        self.cache_metas[objetivo] = disyuncion(valores) if valores else "D"
        return self.cache_metas[objetivo]

    def premisas_pendientes(self, objetivo, visitados=None):
        """Devuelve preguntas aún necesarias para una meta indeterminada."""
        visitados = set() if visitados is None else visitados
        if objetivo in visitados or self.demostrar(objetivo) != "D":
            return set()
        if objetivo in self.preguntas:
            return {objetivo}
        visitados = visitados | {objetivo}
        resultado = set()
        for regla in self.reglas:
            if regla["conclusion"] == objetivo and evaluar(regla["condicion"], self.demostrar) == "D":
                resultado.update(self.premisas_pendientes_nodo(regla["condicion"], visitados))
        return resultado

    def premisas_pendientes_nodo(self, nodo, visitados):
        """Encuentra preguntas desconocidas dentro de una condición lógica."""
        if evaluar(nodo, self.demostrar) != "D":
            return set()
        if "hecho" in nodo:
            return self.premisas_pendientes(nodo["hecho"], visitados)
        if "no" in nodo:
            return self.premisas_pendientes_nodo(nodo["no"], visitados)
        return set().union(*(self.premisas_pendientes_nodo(n, visitados) for n in nodo.get("todos", nodo.get("alguno", []))))


def ejecutar(base_conocimientos, hechos, modo="adelante", objetivo="C27"):
    """Ejecuta un mecanismo de inferencia y prepara resultados y explicaciones."""
    validar_hechos(base_conocimientos, hechos)
    salidas = {c["id"]: c for c in base_conocimientos["conclusiones"] + base_conocimientos["recomendaciones"]}
    if modo not in ("adelante", "atras") or not isinstance(objetivo, str) or objetivo not in salidas:
        raise ValueError("Modo u objetivo inválido")
    hechos_seguros, conflictos, bloqueados = consistencia(base_conocimientos, hechos)
    busqueda = EncadenamientoAtras(base_conocimientos, hechos_seguros)
    goal_value = busqueda.demostrar(objetivo)
    faltantes = busqueda.premisas_pendientes(objetivo)
    if modo == "adelante":
        memoria, pasos = adelante(base_conocimientos, hechos_seguros)
        # Puntuar solo ramas aún indeterminadas; las respondidas D no se repiten.
        prioridades = Counter()
        for clave in salidas:
            if clave not in memoria:
                for pregunta in busqueda.premisas_pendientes(clave):
                    prioridades[pregunta] += 1
        candidatas = sorted((q for q in prioridades if q not in hechos and q not in bloqueados), key=lambda q: (-prioridades[q], q))
        considered = [r["id"] for r in base_conocimientos["reglas"]]
    else:
        pasos = busqueda.pasos
        memoria = {**hechos_seguros, **{clave: "V" for clave, valor in busqueda.cache_metas.items() if valor == "V"}}
        candidatas = sorted(q for q in faltantes if q not in hechos and q not in bloqueados)
        considered = busqueda.reglas_visitadas
    resultados = []
    for clave, elemento in salidas.items():
        if memoria.get(clave) == "V":
            resultados.append({**elemento, "justificaciones": [t["regla"] for t in pasos if t["conclusion"] == clave]})
    return {"modo": modo, "hechos": hechos, "hechos_efectivos": hechos_seguros,
            "objetivo": {"id": objetivo, "estado": goal_value, "etiqueta": ESTADOS[goal_value], "faltantes": sorted(faltantes)},
            "resultados": resultados, "traza": pasos, "conflictos": conflictos,
            "bloqueados": sorted(bloqueados), "preguntas_siguientes": candidatas,
            "reglas_examinadas": considered,
            "resumen": "Se obtuvieron resultados sustentados." if resultados else "Información insuficiente o ninguna regla aplicable; esto no demuestra ausencia de problemas."}


def comparar(base_conocimientos, hechos, objetivo):
    """Compara el sustento de la misma meta mediante los dos encadenamientos."""
    hacia_adelante = ejecutar(base_conocimientos, hechos, "adelante", objetivo)
    hacia_atras = ejecutar(base_conocimientos, hechos, "atras", objetivo)
    return {"adelante": hacia_adelante, "atras": hacia_atras,
            "misma_meta": any(r["id"] == objetivo for r in hacia_adelante["resultados"]) == (hacia_atras["objetivo"]["estado"] == "V"),
            "nota": "Adelante reúne todas las conclusiones alcanzables; atrás recorre las dependencias del objetivo. Se compara el sustento del mismo objetivo, no la cantidad total de resultados."}
