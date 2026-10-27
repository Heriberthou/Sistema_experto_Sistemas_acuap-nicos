"""Encadenamientos propios sobre la misma base y evaluador, sin librerías de IA."""
from .logica import evaluar
from .validacion import validar_hechos, revisar_consistencia, hipotesis_suspendidas
from .explicacion import registrar_paso, reunir_resultados, explicar_resultado
from .calidad import nivel_calidad, calcular_sustento
from .escaleras import habilitada

ESTADOS = {"V": "Sustentada", "F": "No sustentable con los datos conocidos", "D": "Información pendiente"}
SEGURIDAD = ("A06", "A09")


def adelante(base, hechos, bloqueadas=frozenset()):
    """Activa cada regla una vez hasta alcanzar el punto fijo de la memoria.

    Las reglas cuyo consecuente está bloqueado (conclusión descartada o suspendida)
    no se activan; el resto de la inferencia continúa.
    """
    memoria, activadas, pasos = dict(hechos), set(), []

    def resolver(identificador):
        """Lee la memoria sin interpretar una conclusión ausente como falsa."""
        valor = memoria.get(identificador, "D" if identificador.startswith("Q") else "F")
        return valor, [identificador] if valor == "D" and identificador.startswith("Q") else []

    while True:
        hubo_activacion = False
        for regla in base["reglas"]:
            if regla["id"] in activadas or regla["entonces"] in bloqueadas:
                continue
            estado, evidencias, _ = evaluar(regla["si"], resolver)
            if estado == "V":
                activadas.add(regla["id"])
                memoria[regla["entonces"]] = "V"
                pasos.append(registrar_paso(regla, evidencias))
                hubo_activacion = True
        if not hubo_activacion:
            return memoria, pasos


class EncadenamientoAtras:
    """Prueba metas con cortocircuito, caché y protección contra ciclos."""

    def __init__(motor, base, hechos, bloqueadas=frozenset()):
        """Crea una memoria de búsqueda exclusiva para esta consulta."""
        motor.hechos, motor.bloqueadas = hechos, bloqueadas
        motor.preguntas = {pregunta["id"]: pregunta for pregunta in base["preguntas"]}
        motor.reglas = base["reglas"]
        motor.resueltos, motor.en_curso = {}, set()
        motor.pasos, motor.reglas_examinadas, motor.preguntas_consultadas = [], [], []

    def demostrar(motor, objetivo):
        """Devuelve (estado, faltantes); termina en la primera prueba V."""
        if objetivo in motor.preguntas:
            if objetivo not in motor.preguntas_consultadas:
                motor.preguntas_consultadas.append(objetivo)
            padre = motor.preguntas[objetivo].get("padre")
            if padre:
                # Un escalón o síntoma dependiente se prueba a través de su padre (puede preguntar el escalón anterior).
                valor_padre, faltantes = motor.demostrar(padre)
                if valor_padre == "D":
                    return "D", faltantes
                if valor_padre != motor.preguntas[objetivo]["valor_padre"]:
                    return "F", []
            valor = motor.hechos.get(objetivo, "D")
            return valor, [objetivo] if valor == "D" else []
        if objetivo in motor.resueltos:
            return motor.resueltos[objetivo]
        if objetivo in motor.en_curso:
            return "D", []
        motor.en_curso.add(objetivo)
        estado_meta, pendientes = "F", []
        for regla in motor.reglas:
            if regla["entonces"] != objetivo or objetivo in motor.bloqueadas:
                continue
            motor.reglas_examinadas.append(regla["id"])
            estado, evidencias, faltantes = evaluar(regla["si"], motor.demostrar)
            if estado == "V":
                motor.pasos.append(registrar_paso(regla, evidencias))
                motor.resueltos[objetivo] = ("V", [])
                motor.en_curso.remove(objetivo)
                return "V", []
            if estado == "D":
                estado_meta = "D"
                pendientes.extend(hecho for hecho in faltantes if hecho not in pendientes)
        motor.en_curso.remove(objetivo)
        motor.resueltos[objetivo] = (estado_meta, pendientes)
        return estado_meta, pendientes


def preparar(base, hechos, descartadas=frozenset()):
    """Valida, aplica K1-K9, calcula la calidad y devuelve el contexto común de una consulta."""
    validar_hechos(base, hechos)
    seguros, violaciones, avisos = revisar_consistencia(base, hechos)
    bloqueadas = set(descartadas) | hipotesis_suspendidas(avisos)
    calidad = nivel_calidad(hechos, seguros, violaciones, avisos)
    return seguros, violaciones, avisos, bloqueadas, calidad


def filtrar_por_calidad(resultados, calidad):
    """Con calidad No fiable solo se emiten A06 y A09."""
    if calidad["nivel"] == "No fiable":
        return [elemento for elemento in resultados if elemento["id"] in SEGURIDAD]
    return resultados


def ejecutar(base, hechos, modo="adelante", objetivo="A01"):
    """Prepara la memoria y devuelve un informe reproducible del mecanismo elegido."""
    seguros, violaciones, avisos, bloqueadas, calidad = preparar(base, hechos)
    salidas = {elemento["id"] for elemento in base["conclusiones"] + base["recomendaciones"]}
    if modo not in ("adelante", "atras") or not isinstance(objetivo, str) or objetivo not in salidas:
        raise ValueError("Modo u objetivo desconocido")
    sustento = calcular_sustento(base)
    busqueda = EncadenamientoAtras(base, seguros, bloqueadas)
    estado, pendientes = busqueda.demostrar(objetivo)
    if modo == "adelante":
        memoria, pasos = adelante(base, seguros, bloqueadas)
        faltantes = []
        auxiliar = EncadenamientoAtras(base, seguros, bloqueadas)
        for identificador in sorted(salidas):
            _, desconocidos = auxiliar.demostrar(identificador)
            faltantes.extend(hecho for hecho in desconocidos if hecho not in faltantes)
        examinadas = [regla["id"] for regla in base["reglas"]]
        consultadas = list(hechos)
    else:
        memoria = {**seguros, **{identificador: "V" for identificador, (valor, _) in busqueda.resueltos.items() if valor == "V"}}
        pasos, faltantes = busqueda.pasos, pendientes
        examinadas = busqueda.reglas_examinadas
        # Un escalón cuya compuerta lo excluye toma su valor implícito y no cuenta como pregunta planteada.
        consultadas = [q for q in busqueda.preguntas_consultadas if habilitada(base, hechos, q)]
    resultados = filtrar_por_calidad(reunir_resultados(base, memoria, pasos, sustento), calidad)
    resumen = "Hay resultados respaldados por tus respuestas."
    if calidad["nivel"] == "Insuficiente" or (not resultados and faltantes):
        resumen = "Información insuficiente: faltan observaciones o mediciones."
    elif not resultados:
        resumen = "Ninguna regla aplicable. Esto no demuestra que el sistema esté libre de problemas."
    return {"modo": modo, "hechos": hechos, "hechos_efectivos": seguros,
            "objetivo": {"id": objetivo, "estado": estado, "etiqueta": ESTADOS[estado], "faltantes": pendientes},
            "resultados": resultados, "traza": pasos, "conflictos": violaciones, "avisos": avisos, "calidad": calidad,
            "faltantes": faltantes, "reglas_examinadas": examinadas, "reglas_activadas": [p["regla"] for p in pasos],
            "preguntas_consultadas": consultadas, "resumen": resumen}


def comparar(base, hechos, objetivo):
    """Contrasta el sustento de una meta, no la cantidad total de conclusiones."""
    resultado_adelante = ejecutar(base, hechos, "adelante", objetivo)
    resultado_atras = ejecutar(base, hechos, "atras", objetivo)
    derivada = any(elemento["id"] == objetivo for elemento in resultado_adelante["resultados"])
    return {"adelante": resultado_adelante, "atras": resultado_atras,
            "coinciden": derivada == (resultado_atras["objetivo"]["estado"] == "V"),
            "nota": "Adelante reúne todas las conclusiones alcanzables. Atrás prueba una meta y se detiene al sustentarla."}
