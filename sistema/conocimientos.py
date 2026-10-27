"""Carga y valida la base editable antes de iniciar el servidor."""
import json
from pathlib import Path as Ruta

from .logica import simbolos

RAIZ_PROYECTO = Ruta(__file__).resolve().parents[1]
CAMPOS_REGLA = ("id", "si", "expresion", "entonces", "explicacion", "cita", "fuentes")


def cargar_conocimientos(ruta=RAIZ_PROYECTO / "conocimientos/base_conocimientos.json"):
    """Lee JSON y comprueba tipos, símbolos, escaleras, fuentes, prioridades y ciclos."""
    base = json.loads(Ruta(ruta).read_text(encoding="utf-8"))
    preguntas = {pregunta["id"]: pregunta for pregunta in base["preguntas"]}
    salidas = {elemento["id"] for elemento in base["conclusiones"] + base["recomendaciones"]}
    fuentes = {fuente["id"] for fuente in base["fuentes"]}
    for categoria in ("preguntas", "conclusiones", "recomendaciones", "reglas", "fuentes", "restricciones", "parametros"):
        identificadores = [elemento["id"] for elemento in base[categoria]]
        if len(identificadores) != len(set(identificadores)):
            raise ValueError(f"Identificadores duplicados en {categoria}")
    if set(preguntas) & salidas:
        raise ValueError("Una pregunta no puede ser también una conclusión")

    # Cada pregunta con padre debe aparecer después de él y el padre debe existir.
    vistos = set()
    for pregunta in base["preguntas"]:
        padre = pregunta.get("padre")
        if padre and (padre not in vistos or pregunta.get("valor_padre") not in ("V", "F")):
            raise ValueError(f"Padre inválido en {pregunta['id']}")
        vistos.add(pregunta["id"])

    def validar_nodo(nodo, permite_conclusiones=True):
        """Acepta exclusivamente la gramática documentada de antecedentes."""
        if not isinstance(nodo, dict):
            raise ValueError("La condición debe ser un objeto")
        claves = set(nodo)
        if claves == {"c"}:
            if not permite_conclusiones or nodo["c"] not in salidas:
                raise ValueError("Conclusión desconocida")
        elif claves == {"q", "es"}:
            if nodo["q"] not in preguntas or nodo["es"] not in ("V", "F", "D"):
                raise ValueError("Literal booleano inválido")
        elif claves == {"no"}:
            if simbolos(nodo) - set(preguntas):
                raise ValueError("NO solo puede aplicarse a hechos iniciales")
            validar_nodo(nodo["no"], permite_conclusiones)
        elif claves in ({"y"}, {"o"}):
            hijos = next(iter(nodo.values()))
            if not isinstance(hijos, list) or not hijos:
                raise ValueError("Y/O requiere una lista no vacía")
            for hijo in hijos:
                validar_nodo(hijo, permite_conclusiones)
        else:
            raise ValueError("Estructura de condición desconocida")

    grafo = {identificador: set() for identificador in salidas}
    for regla in base["reglas"]:
        if any(campo not in regla for campo in CAMPOS_REGLA):
            raise ValueError(f"Regla incompleta: {regla.get('id')}")
        validar_nodo(regla["si"])
        if regla["entonces"] not in salidas:
            raise ValueError("Consecuente desconocido")
        if not regla["fuentes"] or set(regla["fuentes"]) - fuentes:
            raise ValueError("Fuente desconocida")
        grafo[regla["entonces"]].update(simbolos(regla["si"]) & salidas)
    activos, visitados = set(), set()

    def visitar(identificador):
        """Detecta un ciclo mediante una pila de búsqueda en profundidad."""
        if identificador in activos:
            raise ValueError(f"Ciclo detectado en {identificador}")
        if identificador in visitados:
            return
        activos.add(identificador)
        for dependencia in grafo[identificador]:
            visitar(dependencia)
        activos.remove(identificador)
        visitados.add(identificador)

    for identificador in grafo:
        visitar(identificador)
    for restriccion in base["restricciones"]:
        if restriccion.get("si"):
            validar_nodo(restriccion["si"], permite_conclusiones=False)
        for par in restriccion.get("pares", []):
            if len(par) != 3 or par[0] not in preguntas or par[1] not in preguntas or par[2] not in ("V", "F"):
                raise ValueError("Par K9 inválido")
    for parametro in base["parametros"]:
        if set(parametro["escalera"]) - set(preguntas):
            raise ValueError("Parámetro con preguntas desconocidas")
    for recomendacion in base["recomendaciones"]:
        if type(recomendacion["prioridad"]) is not int or recomendacion["prioridad"] < 1:
            raise ValueError("Prioridad inválida")
        pasos = recomendacion.get("pasos", [])
        if type(pasos) is not list or any(type(paso) is not str or not paso.strip() for paso in pasos):
            raise ValueError("Pasos inválidos")
    if len({recomendacion["prioridad"] for recomendacion in base["recomendaciones"]}) != len(base["recomendaciones"]):
        raise ValueError("Prioridades repetidas")
    base["reglas"].sort(key=lambda regla: int(regla["id"][1:]))
    base["recomendaciones"].sort(key=lambda recomendacion: recomendacion["prioridad"])
    return base
