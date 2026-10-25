"""Casos públicos: python -m unittest discover -s tests -v."""
import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from sistema.inferencia import EncadenamientoAtras, comparar, adelante, ejecutar
from sistema.conocimientos import RAIZ_PROYECTO, cargar_conocimientos
from sistema.logica import conjuncion, disyuncion, negar


class PruebasInferencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = cargar_conocimientos()

    def test_tablas_verdad(self):
        rows = [('V','V','V','V'),('V','F','F','V'),('V','D','D','V'),
                ('F','V','F','V'),('F','F','F','F'),('F','D','F','D'),
                ('D','V','D','V'),('D','F','F','D'),('D','D','D','D')]
        for a,b,and_value,or_value in rows:
            self.assertEqual(conjuncion([a,b]), and_value)
            self.assertEqual(disyuncion([a,b]), or_value)
        self.assertEqual([negar(v) for v in ('V','F','D')], ['F','V','D'])

    def test_ejemplos_reglas_resultados(self):
        ejemplos = json.loads((RAIZ_PROYECTO / 'conocimientos/ejemplos.json').read_text(encoding='utf-8'))
        for example in ejemplos:
            with self.subTest(example=example['id']):
                resultado = ejecutar(self.kb, example['hechos'], objetivo=example['objetivo'])
                self.assertEqual({c['id'] for c in resultado['resultados']}, set(example['esperados']))
                self.assertEqual({s['regla'] for s in resultado['traza']}, set(example['reglas_esperadas']))

    def test_encadenamiento_atras(self):
        resultado = ejecutar(self.kb, {'Q02':'V','Q16':'V'}, 'atras', 'A01')
        self.assertEqual(resultado['objetivo']['estado'], 'V')
        self.assertEqual([s['regla'] for s in resultado['traza']], ['R02','R33','R37'])
        self.assertEqual(resultado['traza'][1]['premisas'], {'C02':'V','Q16':'V'})
        self.assertFalse(resultado['preguntas_siguientes'])

    def test_desconocido_no_es_falso(self):
        desconocido = ejecutar(self.kb, {'Q02':'D','Q16':'V'}, 'atras', 'C27')
        negativo = ejecutar(self.kb, {'Q02':'F','Q16':'V'}, 'atras', 'C27')
        self.assertEqual(desconocido['objetivo']['estado'], 'D')
        self.assertEqual(desconocido['objetivo']['faltantes'], ['Q02'])
        self.assertEqual(negativo['objetivo']['estado'], 'F')
        self.assertNotIn('Q02', desconocido['preguntas_siguientes'])
        self.assertFalse(ejecutar(self.kb, {'Q23':'D'}, 'atras', 'C31')['resultados'])

    def test_preguntas_adaptativas(self):
        self.assertEqual(ejecutar(self.kb, {}, 'atras', 'C27')['preguntas_siguientes'], ['Q02','Q16'])
        self.assertEqual(ejecutar(self.kb, {'Q02':'V'}, 'atras', 'C27')['preguntas_siguientes'], ['Q16'])
        self.assertFalse(ejecutar(self.kb, {'Q02':'F'}, 'atras', 'C27')['preguntas_siguientes'])

    def test_conflicto_y_correccion(self):
        resultado = ejecutar(self.kb, {'Q01':'V','Q03':'F','Q31':'V'})
        self.assertEqual(resultado['bloqueados'], ['Q01','Q03'])
        self.assertEqual({c['id'] for c in resultado['resultados']}, {'C19','A11'})
        fixed = ejecutar(self.kb, {'Q01':'V','Q03':'V','Q31':'V'})
        self.assertFalse(fixed['conflictos'])
        self.assertIn('C01', {c['id'] for c in fixed['resultados']})

    def test_reinicio_y_sin_regla_aplicable(self):
        ejecutar(self.kb, {'Q14':'V'})
        self.assertEqual(ejecutar(self.kb, {'Q01':'F'})['resultados'], [])
        self.assertEqual(ejecutar(self.kb, {})['traza'], [])

    def test_entradas_invalidas(self):
        for hechos in ({'Q99':'V'}, {'C01':'V'}, {'Q01':True}, {'Q01':'yes'}, []):
            with self.assertRaises(ValueError):
                ejecutar(self.kb, hechos)
        with self.assertRaises(ValueError):
            ejecutar(self.kb, {}, objetivo='C99')

    def test_justificaciones_multiples(self):
        kb = copy.deepcopy(self.kb)
        extra = copy.deepcopy(kb['reglas'][0]); extra['id'] = 'R52'
        kb['reglas'].append(extra)
        resultado = ejecutar(kb, {'Q01':'V'})
        self.assertEqual(next(c for c in resultado['resultados'] if c['id']=='C01')['justificaciones'], ['R01','R52'])

    def test_prevencion_de_ciclos(self):
        kb = copy.deepcopy(self.kb)
        kb['reglas'][0]['condicion'] = {'hecho':'C01','valor':'V'}
        with tempfile.TemporaryDirectory() as directorio:
            for clave,valor in kb.items():
                Path(directorio,f'{clave}.json').write_text(json.dumps(valor),encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Ciclo'):
                cargar_conocimientos(directorio)
        self.assertEqual(EncadenamientoAtras(kb, {}).demostrar('C01'), 'D')
        self.assertFalse(adelante(kb, {})[1])

    def test_coincidencia_de_motores(self):
        rng = random.Random(42)
        metas = [c['id'] for c in self.kb['conclusiones'] + self.kb['recomendaciones']]
        for _ in range(15):
            hechos = {q['id']:rng.choice(['V','F','D']) for q in self.kb['preguntas']}
            salidas = {r['id'] for r in ejecutar(self.kb, hechos)['resultados']}
            for objetivo in metas:
                hacia_atras = ejecutar(self.kb, hechos, 'atras', objetivo)
                self.assertEqual(objetivo in salidas, hacia_atras['objetivo']['estado']=='V', objetivo)

    def test_comparacion(self):
        resultado = comparar(self.kb, {'Q02':'V','Q16':'V','Q31':'V'}, 'C27')
        self.assertTrue(resultado['misma_meta'])
        self.assertGreater(len(resultado['adelante']['resultados']),len(resultado['atras']['resultados']))
