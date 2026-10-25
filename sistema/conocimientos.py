"""Carga y validación del vocabulario y las reglas editables, sin eval()."""
import json
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]


def dependencias(nodo):
    """Obtiene los identificadores de hechos mencionados en una condición."""
    if "hecho" in nodo:
        return {nodo["hecho"]}
    if "no" in nodo:
        return dependencias(nodo["no"])
    return set().union(*(dependencias(n) for n in nodo.get("todos", nodo.get("alguno", []))))


def cargar_conocimientos(directorio=RAIZ_PROYECTO / "conocimientos"):
    """Carga los catálogos JSON y comprueba identificadores, referencias y ciclos."""
    nombres = ("preguntas", "conclusiones", "recomendaciones", "reglas", "fuentes", "consistencia")
    base_conocimientos = {nombre: json.loads((Path(directorio) / f"{nombre}.json").read_text(encoding="utf-8")) for nombre in nombres}
    for nombre in nombres[:-1]:
        ids = [elemento["id"] for elemento in base_conocimientos[nombre]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Identificadores duplicados en {nombre}")
    preguntas = {q["id"] for q in base_conocimientos["preguntas"]}
    salidas = {c["id"] for c in base_conocimientos["conclusiones"] + base_conocimientos["recomendaciones"]}
    if preguntas & salidas:
        raise ValueError("Preguntas y resultados deben tener identificadores diferentes")
    fuentes = {s["id"] for s in base_conocimientos["fuentes"]}

    def validar_condicion(nodo):
        """Comprueba la estructura lógica de un antecedente y sus símbolos."""
        if not isinstance(nodo, dict):
            raise ValueError("Una condición debe ser un objeto")
        if set(nodo) == {"hecho", "valor"}:
            if nodo["hecho"] not in preguntas | salidas or nodo["valor"] not in ("V", "F"):
                raise ValueError(f"Literal inválido: {nodo}")
            if nodo["hecho"] in salidas and nodo["valor"] == "F":
                raise ValueError("No se permite negar un resultado no demostrado")
        elif set(nodo) == {"no"}:
            if dependencias(nodo) - preguntas:
                raise ValueError("NO solo admite hechos observables; no ausencia de derivaciones")
            validar_condicion(nodo["no"])
        elif set(nodo) in ({"todos"}, {"alguno"}):
            hijos = next(iter(nodo.values()))
            if not isinstance(hijos, list) or not hijos:
                raise ValueError("Y/O requiere una lista no vacía")
            for hijo in hijos:
                validar_condicion(hijo)
        else:
            raise ValueError(f"Operador inválido: {nodo}")

    grafo = {clave: set() for clave in salidas}
    for regla in base_conocimientos["reglas"]:
        validar_condicion(regla["condicion"])
        if regla["conclusion"] not in salidas:
            raise ValueError(f"Consecuente desconocido: {regla['id']}")
        if not regla["fuentes"] or set(regla["fuentes"]) - fuentes:
            raise ValueError(f"Fuentes inválidas: {regla['id']}")
        grafo[regla["conclusion"]].update(dependencias(regla["condicion"]) & salidas)
    visitados, activos = set(), set()

    def visitar(clave):
        """Detecta referencias circulares entre conclusiones mediante recorrido en profundidad."""
        if clave in activos:
            raise ValueError(f"Ciclo en la base de conocimientos: {clave}")
        if clave in visitados:
            return
        activos.add(clave)
        for dep in grafo[clave]:
            visitar(dep)
        activos.remove(clave)
        visitados.add(clave)

    for clave in grafo:
        visitar(clave)
    for comprobar in base_conocimientos["consistencia"]:
        if comprobar["si_hecho"] not in preguntas or comprobar["entonces_hecho"] not in preguntas:
            raise ValueError("La consistencia debe referirse a preguntas conocidas")
        if comprobar["si_valor"] not in ("V", "F") or comprobar["entonces_valor"] not in ("V", "F"):
            raise ValueError("Valor de consistencia inválido")
    base_conocimientos["reglas"].sort(key=lambda regla: regla["id"])
    return base_conocimientos
