"""Minimizing Lateness aplicado à fila de chamados de um técnico de plantão.

Problema: um único técnico; n chamados, cada um com duração t_j e prazo de SLA
d_j; todos já estão na fila no início do turno. Escolher a ordem de atendimento
que minimiza o ATRASO MÁXIMO  L = max_j (fim_j - d_j).

Algoritmo guloso (Kleinberg & Tardos, 4.2): atender em ordem crescente de prazo —
Earliest Deadline First (EDF). Complexidade O(n log n) (é só uma ordenação).

Otimalidade (argumento de troca): toda ordem ótima pode ser transformada em EDF
sem piorar o atraso máximo. Se em alguma ordem um chamado i vem imediatamente
antes de j mas d_i > d_j (uma "inversão"), trocar os dois não aumenta o atraso
máximo: j passa a terminar antes, e i passa a terminar onde j terminava, mas
d_i > d_j, logo o atraso de i na nova posição é menor que o atraso que j tinha.
Removendo todas as inversões chega-se à ordem EDF com atraso máximo ≤ ao original.

O módulo também simula ordens "intuitivas" (FIFO, menor duração primeiro,
prioridade declarada) para evidenciar no log que o EDF domina todas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .modelos import Chamado
from .tempo import duracao_legivel, min_para_hm

log = logging.getLogger("EDF")


@dataclass(frozen=True)
class Atendimento:
    chamado: Chamado
    inicio: int
    fim: int

    @property
    def atraso(self) -> int:
        """Minutos além do prazo do SLA (0 se atendido dentro do prazo)."""
        return max(0, self.fim - self.chamado.prazo)


@dataclass
class Escalonamento:
    estrategia: str
    atendimentos: list[Atendimento]

    @property
    def atraso_maximo(self) -> int:
        return max((a.atraso for a in self.atendimentos), default=0)

    @property
    def atrasados(self) -> list[Atendimento]:
        return [a for a in self.atendimentos if a.atraso > 0]

    @property
    def fim(self) -> int:
        return self.atendimentos[-1].fim if self.atendimentos else 0


def simular(ordem: list[Chamado], inicio: int, estrategia: str) -> Escalonamento:
    """Executa os chamados na ordem dada, sem ociosidade, a partir de `inicio`."""
    t = inicio
    atendimentos: list[Atendimento] = []
    for c in ordem:
        a = Atendimento(c, t, t + c.duracao)
        atendimentos.append(a)
        t = a.fim
    return Escalonamento(estrategia, atendimentos)


def escalonar_edf(chamados: list[Chamado], inicio: int) -> Escalonamento:
    """Earliest Deadline First, com log passo a passo."""
    log.info("Passo 1 — ordenar %d chamados por prazo de SLA (menor prazo primeiro)", len(chamados))
    ordem = sorted(chamados, key=lambda c: (c.prazo, c.id))

    log.info("Passo 2 — atender nessa ordem, sem intervalos ociosos, a partir de %s", min_para_hm(inicio))
    resultado = simular(ordem, inicio, "EDF (menor prazo primeiro)")
    for n, a in enumerate(resultado.atendimentos, 1):
        c = a.chamado
        situacao = f"ATRASO de {duracao_legivel(a.atraso)}" if a.atraso else "no prazo"
        folga = c.prazo - a.fim
        log.info(
            "%s  #%d %s [%s] %s", min_para_hm(a.inicio), n, c.id, c.prioridade, c.descricao,
        )
        log.info(
            "         duração %s → termina %s | prazo %s | %s%s",
            duracao_legivel(c.duracao), min_para_hm(a.fim), min_para_hm(c.prazo), situacao,
            f" (folga {duracao_legivel(folga)})" if folga > 0 else "",
        )

    log.info("Passo 3 — resultado")
    log.info("         atraso máximo        : %s", _fmt_atraso(resultado.atraso_maximo))
    log.info(
        "         chamados fora do SLA : %d de %d%s",
        len(resultado.atrasados), len(chamados),
        (" (" + ", ".join(a.chamado.id for a in resultado.atrasados) + ")") if resultado.atrasados else "",
    )
    log.info("         fila encerrada às    : %s", min_para_hm(resultado.fim))
    return resultado


def limite_inferior_atraso(chamados: list[Chamado], inicio: int) -> int:
    """Limite inferior simples para o atraso máximo, usado para checar o EDF no log.

    Para qualquer prazo d, todos os chamados com prazo ≤ d somam T minutos de
    trabalho; o último deles termina no mínimo em inicio + T, e tem prazo ≤ d,
    logo alguém atrasa pelo menos (inicio + T - d). O máximo sobre todos os d é
    um limite inferior válido para qualquer ordem.
    """
    melhor = 0
    for d in sorted({c.prazo for c in chamados}):
        trabalho = sum(c.duracao for c in chamados if c.prazo <= d)
        melhor = max(melhor, inicio + trabalho - d)
    return melhor


def comparar_estrategias(chamados: list[Chamado], inicio: int) -> list[Escalonamento]:
    """Simula ordens alternativas para contrastar com o EDF."""
    return [
        simular(list(chamados), inicio, "FIFO (ordem de abertura)"),
        simular(sorted(chamados, key=lambda c: c.duracao), inicio, "SPT (menor duração primeiro)"),
        simular(sorted(chamados, key=lambda c: c.prioridade), inicio, "Prioridade declarada (P1 > P2 > P3)"),
        simular(sorted(chamados, key=lambda c: (c.prazo, c.id)), inicio, "EDF (menor prazo primeiro)"),
    ]


def _fmt_atraso(minutos: int) -> str:
    return duracao_legivel(minutos) if minutos else "0 (todos no prazo)"
