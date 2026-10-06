"""Testes dos dois gulosos contra força bruta em instâncias aleatórias pequenas.

Rodar na raiz do repositório:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import itertools
import logging
import random
import unittest

from helpdesk.interval_partitioning import particionar, profundidade
from helpdesk.minimizing_lateness import (
    comparar_estrategias,
    escalonar_edf,
    limite_inferior_atraso,
    simular,
)
from helpdesk.modelos import Chamado, JanelaManutencao

logging.disable(logging.CRITICAL)  # os testes não precisam do log passo a passo


# ----------------------------------------------------------------- helpers
def janelas_aleatorias(rng: random.Random, n: int) -> list[JanelaManutencao]:
    saida = []
    for i in range(n):
        inicio = rng.randrange(0, 600, 15)
        fim = inicio + rng.randrange(15, 181, 15)
        saida.append(JanelaManutencao(f"J{i}", "", inicio, fim))
    return saida


def chamados_aleatorios(rng: random.Random, n: int) -> list[Chamado]:
    return [
        Chamado(f"C{i}", "", "P3", duracao=rng.randint(5, 60), prazo=rng.randint(480, 900))
        for i in range(n)
    ]


def sem_sobreposicao(janelas: list[JanelaManutencao]) -> bool:
    ordenadas = sorted(janelas, key=lambda j: j.inicio)
    return all(a.fim <= b.inicio for a, b in zip(ordenadas, ordenadas[1:]))


def minimo_forca_bruta_particao(janelas: list[JanelaManutencao]) -> int:
    """Menor k tal que existe uma coloração das janelas em k técnicos compatíveis."""
    n = len(janelas)
    for k in range(1, n + 1):
        for cores in itertools.product(range(k), repeat=n):
            grupos = [[] for _ in range(k)]
            for j, cor in zip(janelas, cores):
                grupos[cor].append(j)
            if all(sem_sobreposicao(g) for g in grupos):
                return k
    return n


def minimo_forca_bruta_atraso(chamados: list[Chamado], inicio: int) -> int:
    return min(simular(list(p), inicio, "").atraso_maximo for p in itertools.permutations(chamados))


# ------------------------------------------------------- Interval Partitioning
class TestIntervalPartitioning(unittest.TestCase):
    def test_vazio(self):
        r = particionar([])
        self.assertEqual(r.num_tecnicos, 0)
        self.assertEqual(r.profundidade, 0)

    def test_janelas_encostadas_compartilham_tecnico(self):
        # [08:00, 10:00) e [10:00, 12:00) não se sobrepõem
        j = [JanelaManutencao("A", "", 480, 600), JanelaManutencao("B", "", 600, 720)]
        self.assertEqual(particionar(j).num_tecnicos, 1)
        self.assertEqual(profundidade(j), 1)

    def test_atribuicao_e_valida(self):
        rng = random.Random(1)
        for _ in range(200):
            janelas = janelas_aleatorias(rng, rng.randint(1, 12))
            r = particionar(janelas)
            atribuidas = [j for grupo in r.atribuicao.values() for j in grupo]
            self.assertCountEqual(atribuidas, janelas)  # toda janela foi atribuída uma vez
            for grupo in r.atribuicao.values():
                self.assertTrue(sem_sobreposicao(grupo))

    def test_igual_a_profundidade(self):
        rng = random.Random(2)
        for _ in range(500):
            janelas = janelas_aleatorias(rng, rng.randint(1, 15))
            r = particionar(janelas)
            self.assertEqual(r.num_tecnicos, profundidade(janelas))

    def test_igual_a_forca_bruta(self):
        rng = random.Random(3)
        for _ in range(60):
            janelas = janelas_aleatorias(rng, rng.randint(1, 6))
            self.assertEqual(particionar(janelas).num_tecnicos, minimo_forca_bruta_particao(janelas))


# --------------------------------------------------------- Minimizing Lateness
class TestMinimizingLateness(unittest.TestCase):
    def test_vazio(self):
        r = escalonar_edf([], 480)
        self.assertEqual(r.atraso_maximo, 0)
        self.assertEqual(r.atendimentos, [])

    def test_sem_ociosidade_e_ordem_por_prazo(self):
        rng = random.Random(4)
        for _ in range(200):
            chamados = chamados_aleatorios(rng, rng.randint(1, 10))
            r = escalonar_edf(chamados, 480)
            prazos = [a.chamado.prazo for a in r.atendimentos]
            self.assertEqual(prazos, sorted(prazos))
            for a, b in zip(r.atendimentos, r.atendimentos[1:]):
                self.assertEqual(a.fim, b.inicio)

    def test_igual_a_forca_bruta(self):
        rng = random.Random(5)
        for _ in range(80):
            chamados = chamados_aleatorios(rng, rng.randint(1, 7))
            self.assertEqual(
                escalonar_edf(chamados, 480).atraso_maximo,
                minimo_forca_bruta_atraso(chamados, 480),
            )

    def test_atinge_limite_inferior(self):
        rng = random.Random(6)
        for _ in range(300):
            chamados = chamados_aleatorios(rng, rng.randint(1, 12))
            edf = escalonar_edf(chamados, 480)
            self.assertEqual(edf.atraso_maximo, max(0, limite_inferior_atraso(chamados, 480)))

    def test_edf_domina_outras_estrategias(self):
        rng = random.Random(7)
        for _ in range(300):
            chamados = chamados_aleatorios(rng, rng.randint(1, 12))
            resultados = comparar_estrategias(chamados, 480)
            edf = next(e for e in resultados if e.estrategia.startswith("EDF"))
            for e in resultados:
                self.assertLessEqual(edf.atraso_maximo, e.atraso_maximo)


if __name__ == "__main__":
    unittest.main()
