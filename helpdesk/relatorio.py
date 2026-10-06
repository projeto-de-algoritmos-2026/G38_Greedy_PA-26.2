"""Renderização em texto: Gantt ASCII dos técnicos e tabelas da fila de chamados."""

from __future__ import annotations

from .interval_partitioning import ResultadoParticao
from .minimizing_lateness import Escalonamento
from .tempo import duracao_legivel, min_para_hm

PASSO = 10  # minutos por coluna do Gantt


def _rotulo(id_: str, largura: int) -> str:
    """Rótulo que cabe no bloco: id completo, só o sufixo numérico, ou nada."""
    if largura >= len(id_) + 2:
        return id_
    sufixo = id_.split("-")[-1]
    if largura >= len(sufixo) + 2:
        return sufixo
    return ""


def gantt_tecnicos(resultado: ResultadoParticao, inicio: int, fim: int) -> list[str]:
    """Uma linha por técnico; cada janela vira um bloco [JM-01====] proporcional."""
    colunas = max(1, (fim - inicio + PASSO - 1) // PASSO)
    linhas: list[str] = []

    # régua de horas
    regua = [" "] * colunas
    for col in range(colunas):
        minuto = inicio + col * PASSO
        if minuto % 60 == 0:
            rotulo = f"{minuto // 60:02d}h"
            for i, ch in enumerate(rotulo):
                if col + i < colunas:
                    regua[col + i] = ch
    linhas.append(" " * 12 + "".join(regua))
    linhas.append(" " * 12 + "".join("|" if (inicio + c * PASSO) % 60 == 0 else "." for c in range(colunas)))

    for tecnico in sorted(resultado.atribuicao):
        celulas = [" "] * colunas
        for j in resultado.atribuicao[tecnico]:
            a = max(0, (j.inicio - inicio) // PASSO)
            b = min(colunas, max(a + 1, (j.fim - inicio) // PASSO))
            largura = b - a
            bloco = list(("[" + _rotulo(j.id, largura) + "=" * colunas)[:largura])
            if largura >= 2:
                bloco[-1] = "]"
            celulas[a:b] = bloco
        linhas.append(f"Técnico {tecnico:<3} " + "".join(celulas))
    return linhas


def tabela_fila(esc: Escalonamento) -> list[str]:
    cab = f"{'#':>2}  {'Chamado':<8} {'Pri':<4} {'Duração':<8} {'Início':<6} {'Fim':<6} {'Prazo':<6} {'Atraso':<8}"
    linhas = [cab, "-" * len(cab)]
    for n, a in enumerate(esc.atendimentos, 1):
        c = a.chamado
        atraso = f"+{duracao_legivel(a.atraso)} ⚠" if a.atraso else "—"
        linhas.append(
            f"{n:>2}  {c.id:<8} {c.prioridade:<4} {duracao_legivel(c.duracao):<8} "
            f"{min_para_hm(a.inicio):<6} {min_para_hm(a.fim):<6} {min_para_hm(c.prazo):<6} {atraso:<8}"
        )
    return linhas


def tabela_comparativa(escalonamentos: list[Escalonamento]) -> list[str]:
    melhor = min(e.atraso_maximo for e in escalonamentos)
    cab = f"{'Estratégia':<38} {'Atraso máx.':>12} {'Fora do SLA':>12}"
    linhas = [cab, "-" * len(cab)]
    for e in escalonamentos:
        marca = "  ◄ ótimo" if e.atraso_maximo == melhor else ""
        linhas.append(
            f"{e.estrategia:<38} {duracao_legivel(e.atraso_maximo) if e.atraso_maximo else '0':>12} "
            f"{len(e.atrasados):>12}{marca}"
        )
    return linhas
