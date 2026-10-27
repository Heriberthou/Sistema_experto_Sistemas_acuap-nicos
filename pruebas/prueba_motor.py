"""Motor: los 32 casos del documento v3, lógica de Kleene, escaleras, K1-K9 y calidad."""
import json
import unittest as pruebas
from sistema.conocimientos import RAIZ_PROYECTO, cargar_conocimientos
from sistema.casos import evaluar_caso
from sistema.escaleras import completar, habilitada
from sistema.logica import evaluar
from sistema.motor import comparar, ejecutar
from sistema.validacion import revisar_consistencia

BASE = cargar_conocimientos()
CASOS = json.loads((RAIZ_PROYECTO / "conocimientos/casos_prueba.json").read_text(encoding="utf-8"))
NUMERO = lambda identificador: int(identificador[1:])


def hechos_del_caso(caso):
    """T4 responde Desconozco a todas las preguntas; los demás casos usan sus hechos."""
    return {pregunta["id"]: "D" for pregunta in BASE["preguntas"]} if caso.get("todo_d") else dict(caso["hechos"])


class PruebasCasos(pruebas.TestCase):
    """Cada caso compara resultados, reglas, orden, calidad, restricciones y encadenamiento hacia atrás."""

    def test_casos_del_documento(caso_prueba):
        """Resultados esperados de T1-T32 (con sus variantes) calculados por la base v3."""
        for caso in CASOS:
            with caso_prueba.subTest(caso["id"]):
                informe = evaluar_caso(BASE, caso)
                caso_prueba.assertEqual(informe["diferencias"], [], informe["id"])

    def test_las_58_reglas_se_activan(caso_prueba):
        """Cobertura: cada regla de la base se activa en al menos uno de los casos válidos."""
        activadas = set()
        for caso in CASOS:
            if not caso.get("error_esperado"):
                activadas.update(ejecutar(BASE, hechos_del_caso(caso), "adelante", caso["objetivo"])["reglas_activadas"])
        caso_prueba.assertEqual(len(BASE["reglas"]), 58)
        caso_prueba.assertEqual({regla["id"] for regla in BASE["reglas"]} - activadas, set())

    def test_ambos_mecanismos_coinciden(caso_prueba):
        """Para cada meta derivada hacia adelante, atrás obtiene V; si no se deriva, atrás no obtiene V."""
        metas = [elemento["id"] for elemento in BASE["conclusiones"] + BASE["recomendaciones"]]
        for caso in CASOS:
            if caso.get("error_esperado") or caso["id"] in ("T20",):
                continue
            for meta in metas:
                with caso_prueba.subTest(caso["id"], meta=meta):
                    caso_prueba.assertTrue(comparar(BASE, hechos_del_caso(caso), meta)["coinciden"])

    def test_reinicio_no_conserva_hechos(caso_prueba):
        """T7: ejecutar T2 después de T1 es idéntico a ejecutar T2 solo."""
        primero = {c["id"]: c for c in CASOS}
        ejecutar(BASE, primero["T1"]["hechos"])
        despues = ejecutar(BASE, primero["T7"]["hechos"])
        solo = ejecutar(BASE, primero["T2"]["hechos"])
        caso_prueba.assertEqual([r["id"] for r in despues["resultados"]], [r["id"] for r in solo["resultados"]])
        caso_prueba.assertTrue({"C01", "C10", "C12", "A01", "A05"}.isdisjoint(r["id"] for r in despues["resultados"]))


class PruebasLogicaYEscaleras(pruebas.TestCase):
    """Kleene, comparación explícita con D, valores implícitos y habilitación de escalones."""

    @staticmethod
    def valor(nodo, **hechos):
        """Evalúa un nodo con hechos fijos; lo no informado es D."""
        return evaluar(nodo, lambda identificador: (hechos.get(identificador, "D"), []))[0]

    def test_kleene(caso_prueba):
        """Un F domina la conjunción, un V la disyunción y la negación conserva D."""
        q = lambda i, v="V": {"q": i, "es": v}
        caso_prueba.assertEqual(caso_prueba.valor({"y": [q("Q01a"), q("Q06")]}, Q01a="F"), "F")
        caso_prueba.assertEqual(caso_prueba.valor({"y": [q("Q01a"), q("Q06")]}, Q01a="V"), "D")
        caso_prueba.assertEqual(caso_prueba.valor({"o": [q("Q01a"), q("Q06")]}, Q01a="V"), "V")
        caso_prueba.assertEqual(caso_prueba.valor({"o": [q("Q01a"), q("Q06")]}, Q01a="F"), "D")
        caso_prueba.assertEqual(caso_prueba.valor({"no": q("Q17")}), "D")
        caso_prueba.assertEqual(caso_prueba.valor({"no": q("Q17")}, Q17="F"), "V")

    def test_comparacion_explicita_con_d(caso_prueba):
        """«= D» vale V solo con Desconozco y nunca queda como dato faltante (R16)."""
        nodo = {"q": "Q13", "es": "D"}
        caso_prueba.assertEqual(caso_prueba.valor(nodo, Q13="D"), "V")
        caso_prueba.assertEqual(caso_prueba.valor(nodo, Q13="F"), "F")
        caso_prueba.assertEqual(evaluar(nodo, lambda i: ("D", ["Q13"]))[2], [])

    def test_valores_implicitos(caso_prueba):
        """F si el padre excluye el intervalo; D si el padre es D o falta."""
        caso_prueba.assertEqual(completar(BASE, {"Q04a": "F"})["Q04c"], "F")
        caso_prueba.assertEqual(completar(BASE, {"Q04a": "D"})["Q04b"], "D")
        caso_prueba.assertEqual(completar(BASE, {"Q04a": "V"})["Q04b"], "D")
        caso_prueba.assertEqual(completar(BASE, {"Q03a": "V"})["Q03b"], "F")
        caso_prueba.assertEqual(completar(BASE, {"Q03a": "F", "Q03b": "F"})["Q03c"], "F")
        caso_prueba.assertEqual(completar(BASE, {"Q21": "F"})["Q23"], "F")
        caso_prueba.assertEqual(completar(BASE, {"Q15": "F"})["Q27"], "F")
        caso_prueba.assertEqual(completar(BASE, {"Q21": "V"})["Q23"], "D")

    def test_habilitacion(caso_prueba):
        """Un escalón o síntoma dependiente solo se plantea con el valor de padre que lo habilita."""
        caso_prueba.assertFalse(habilitada(BASE, {}, "Q01b"))
        caso_prueba.assertTrue(habilitada(BASE, {"Q01a": "V"}, "Q01b"))
        caso_prueba.assertFalse(habilitada(BASE, {"Q01a": "D"}, "Q01b"))
        caso_prueba.assertTrue(habilitada(BASE, {"Q02a": "F"}, "Q02c"))
        caso_prueba.assertTrue(habilitada(BASE, {"Q21": "V"}, "Q25"))
        caso_prueba.assertFalse(habilitada(BASE, {"Q21": "F"}, "Q25"))
        caso_prueba.assertTrue(habilitada(BASE, {"Q15": "V"}, "Q27"))
        caso_prueba.assertTrue(habilitada(BASE, {}, "Q15") and habilitada(BASE, {}, "Q21"))

    def test_limites_exactos_de_las_preguntas_de_rango(caso_prueba):
        """Cada umbral activa su condición solo con la respuesta Sí a su pregunta de rango."""
        pruebas_umbral = {"C01": ("Q01a", "C01"), "C04": ("Q04a", "C04"), "C05": ("Q05a", "C05")}
        for conclusion, (pregunta, esperada) in pruebas_umbral.items():
            caso_prueba.assertIn(esperada, [r["id"] for r in ejecutar(BASE, {pregunta: "V"})["resultados"]])
            caso_prueba.assertNotIn(esperada, [r["id"] for r in ejecutar(BASE, {pregunta: "F"})["resultados"]])
            caso_prueba.assertNotIn(esperada, [r["id"] for r in ejecutar(BASE, {pregunta: "D"})["resultados"]])


class PruebasRestriccionesYCalidad(pruebas.TestCase):
    """K1-K9: contradicciones, avisos, suspensiones y nivel de calidad."""

    def revisar(caso_prueba, hechos):
        """Devuelve los identificadores de violaciones y avisos y los hechos efectivos."""
        seguros, violaciones, avisos = revisar_consistencia(BASE, hechos)
        return [v["id"] for v in violaciones], [a["id"] for a in avisos], seguros

    def test_contradicciones_k1_a_k5(caso_prueba):
        """Cada contradicción trata como D sus hechos y deja las respuestas originales intactas."""
        casos = {"K1": {"Q09": "F", "Q10": "V"}, "K2": {"Q13": "F", "Q14": "V"}, "K3": {"Q10": "F", "Q11": "V"},
                 "K4": {"Q09": "F", "Q14": "V"}, "K5": {"Q18": "F", "Q08": "V"}}
        for identificador, hechos in casos.items():
            original = dict(hechos)
            violaciones, _, seguros = caso_prueba.revisar(hechos)
            caso_prueba.assertEqual(violaciones[0], identificador)
            caso_prueba.assertTrue(all(seguros[h] == "D" for h in hechos))
            caso_prueba.assertEqual(hechos, original)

    def test_avisos_k6_k7_k8(caso_prueba):
        """K6 extremos sin signos, K7 evasiones y K8 patrón en bloque no cambian los hechos."""
        _, avisos, _ = caso_prueba.revisar({"Q18": "V", "Q06": "F", "Q07": "F", "Q04a": "V", "Q04b": "V", "Q04c": "V"})
        caso_prueba.assertIn("K6", avisos)
        _, avisos, _ = caso_prueba.revisar({"Q07": "V", "Q01a": "D", "Q04a": "D", "Q05a": "D"})
        caso_prueba.assertIn("K7a", avisos)
        _, avisos, _ = caso_prueba.revisar({"Q21": "V", "Q15": "F", "Q22": "F", "Q23": "F", "Q24": "F", "Q25": "F", "Q26": "F"})
        caso_prueba.assertIn("K7b", avisos)
        _, avisos, seguros = caso_prueba.revisar({f"Q{n:02d}": "F" for n in range(6, 18)})
        caso_prueba.assertIn("K8", avisos)
        caso_prueba.assertEqual(seguros["Q06"], "F")
        _, avisos, _ = caso_prueba.revisar({f"Q{n:02d}": "F" for n in range(6, 17)})
        caso_prueba.assertNotIn("K8", avisos)

    def test_k9_en_escaleras_y_compuertas(caso_prueba):
        """Una respuesta V incompatible con su padre o con otro escalón se trata como D."""
        for hechos in ({"Q04a": "F", "Q04c": "V"}, {"Q01a": "F", "Q01b": "V"}, {"Q02a": "V", "Q02c": "V"},
                       {"Q03a": "V", "Q03c": "V"}, {"Q21": "F", "Q23": "V"}, {"Q15": "F", "Q27": "V"}):
            with caso_prueba.subTest(hechos):
                violaciones, _, _ = caso_prueba.revisar(dict(hechos))
                caso_prueba.assertIn("K9", violaciones)
        caso_prueba.assertEqual(caso_prueba.revisar({"Q04a": "V", "Q04b": "F"})[0], [])

    def test_k7a_suspende_hipotesis_de_oxigeno(caso_prueba):
        """Con K7(a) activo no se emite C12 aunque C09 y el boqueo lo permitirían."""
        informe = ejecutar(BASE, {"Q07": "V", "Q13": "F", "Q01a": "D", "Q04a": "D", "Q05a": "D"})
        caso_prueba.assertIn("C09", [r["id"] for r in informe["resultados"]])
        caso_prueba.assertNotIn("C12", [r["id"] for r in informe["resultados"]])

    def test_niveles_de_calidad(caso_prueba):
        """Confiable, Parcial, No fiable e Insuficiente según la sección 4.6."""
        caso_prueba.assertEqual(ejecutar(BASE, {})["calidad"]["nivel"], "Insuficiente")
        caso_prueba.assertEqual(ejecutar(BASE, {"Q04a": "D"})["calidad"]["nivel"], "Insuficiente")
        caso_prueba.assertEqual(ejecutar(BASE, {"Q09": "V", "Q10": "V", "Q11": "F"})["calidad"]["nivel"], "Confiable")
        caso_prueba.assertEqual(ejecutar(BASE, {"Q09": "F", "Q13": "V"})["calidad"]["nivel"], "Parcial")
        caso_prueba.assertEqual(ejecutar(BASE, {"Q09": "F", "Q10": "V", "Q13": "F", "Q14": "V"})["calidad"]["nivel"], "No fiable")
        informe = ejecutar(BASE, {f"Q{n:02d}": "V" for n in range(6, 20)})
        caso_prueba.assertEqual([r["id"] for r in informe["resultados"]], ["A06"])

    def test_sustento_de_las_conclusiones(caso_prueba):
        """Medida si viene de una respuesta de rango, Observada si de una observación, Hipótesis si es inferencia."""
        informe = ejecutar(BASE, {"Q01a": "V", "Q07": "V", "Q04a": "V", "Q08": "V", "Q02a": "V"})
        sustento = {r["id"]: r["sustento"] for r in informe["resultados"] if r["id"][0] == "C"}
        caso_prueba.assertEqual(sustento["C01"], "Medida")
        caso_prueba.assertEqual(sustento["C10"], "Observada")
        caso_prueba.assertEqual(sustento["C12"], "Hipótesis")

    def test_entradas_invalidas_no_entran_en_memoria(caso_prueba):
        """Solo V, F o D; identificadores desconocidos, números y booleanos se rechazan."""
        for hechos in ({"Q03a": 12}, {"Q03a": "quizá"}, {"Q99": "V"}, {"Q01a": True}, [1], {"Q01a": None}):
            with caso_prueba.assertRaises(ValueError):
                ejecutar(BASE, hechos)

    def test_base_valida_y_acíclica(caso_prueba):
        """La base declara 34 preguntas, 29 conclusiones, 28 recomendaciones y 58 reglas con fuente y cita."""
        caso_prueba.assertEqual((len(BASE["preguntas"]), len(BASE["conclusiones"]), len(BASE["recomendaciones"]), len(BASE["reglas"])), (34, 29, 28, 58))
        caso_prueba.assertTrue(all(regla["fuentes"] and regla["cita"] for regla in BASE["reglas"]))
        caso_prueba.assertEqual([r["id"] for r in BASE["recomendaciones"]][:3], ["A06", "A21", "A09"])
        caso_prueba.assertEqual(BASE["recomendaciones"][-1]["id"], "A07")

    def test_recomendaciones_con_pasos(caso_prueba):
        """Cada recomendación trae una lista de pasos concretos para el resultado final."""
        for recomendacion in BASE["recomendaciones"]:
            caso_prueba.assertGreaterEqual(len(recomendacion["pasos"]), 2, recomendacion["id"])


if __name__ == "__main__":
    pruebas.main()
