"""Lógica trivaluada de Kleene fuerte: D nunca equivale a F."""


def negar(valor):
    """Invierte V y F sin cambiar D."""
    return {"V": "F", "F": "V", "D": "D"}[valor]


def conjuncion(valores):
    """Aplica Y de Kleene fuerte a una secuencia de valores V/F/D."""
    return "F" if "F" in valores else "D" if "D" in valores else "V"


def disyuncion(valores):
    """Aplica O de Kleene fuerte a una secuencia de valores V/F/D."""
    return "V" if "V" in valores else "D" if "D" in valores else "F"


def evaluar(nodo, resolver):
    """Evalúa recursivamente un antecedente usando la función de consulta de hechos."""
    if "hecho" in nodo:
        valor = resolver(nodo["hecho"])
        return valor if nodo["valor"] == "V" else negar(valor)
    if "no" in nodo:
        return negar(evaluar(nodo["no"], resolver))
    if "todos" in nodo:
        return conjuncion([evaluar(hijo, resolver) for hijo in nodo["todos"]])
    return disyuncion([evaluar(hijo, resolver) for hijo in nodo["alguno"]])
