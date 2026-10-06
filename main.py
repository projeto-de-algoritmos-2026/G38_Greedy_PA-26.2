#!/usr/bin/env python3
"""Escalonador de help desk de TI — demonstração de dois algoritmos gulosos.

Uso:
    python main.py dados/exemplo_turno.json            # log completo no terminal
    python main.py dados/exemplo_turno.json --debug    # também mostra o estado do heap
    python main.py dados/exemplo_turno.json --json saida.json

Só usa a biblioteca padrão do Python (3.10+).
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from pathlib import Path

from helpdesk.interval_partitioning import particionar
from helpdesk.minimizing_lateness import (
    comparar_estrategias,
    escalonar_edf,
    limite_inferior_atraso,
)
from helpdesk.modelos import Entrada, carregar
from helpdesk.relatorio import gantt_tecnicos, tabela_comparativa, tabela_fila
from helpdesk.tempo import duracao_legivel, min_para_hm

log = logging.getLogger("MAIN")
LARGURA = 78


def secao(titulo: str) -> None:
    log.info("")
    log.info("=" * LARGURA)
    log.info("%s", titulo)
    log.info("=" * LARGURA)


def executar(entrada: Entrada, comparar: bool) -> dict:
    secao("ENTRADA")
    log.info("Turno: %s–%s | equipe disponível: %d técnico(s)",
             min_para_hm(entrada.turno_inicio), min_para_hm(entrada.turno_fim), entrada.equipe)
    log.info("%d janela(s) de manutenção com horário fixo | %d chamado(s) na fila",
             len(entrada.janelas), len(entrada.chamados))

    # ---------------------------------------------------------------- IP
    secao("PARTE 1 — INTERVAL PARTITIONING: quantos técnicos as janelas exigem?")
    particao = particionar(entrada.janelas)

    log.info("")
    log.info("Escala resultante:")
    for linha in gantt_tecnicos(particao, entrada.turno_inicio, entrada.turno_fim):
        log.info("  %s", linha)
    for tecnico in sorted(particao.atribuicao):
        ids = ", ".join(j.id for j in particao.atribuicao[tecnico])
        ocupado = sum(j.duracao for j in particao.atribuicao[tecnico])
        log.info("  Técnico %d: %s  (ocupado %s)", tecnico, ids, duracao_legivel(ocupado))

    # --------------------------------------------------------------- EDF
    secao("PARTE 2 — MINIMIZING LATENESS (EDF): em que ordem atender a fila?")
    edf = escalonar_edf(entrada.chamados, entrada.turno_inicio)

    limite = limite_inferior_atraso(entrada.chamados, entrada.turno_inicio)
    log.info("         limite inferior p/ qualquer ordem: %s%s",
             duracao_legivel(limite) if limite > 0 else "0",
             " ⇒ EDF atinge o limite ⇒ ÓTIMO" if edf.atraso_maximo == max(0, limite) else "")

    log.info("")
    log.info("Fila ordenada:")
    for linha in tabela_fila(edf):
        log.info("  %s", linha)

    comparacao = []
    if comparar and entrada.chamados:
        log.info("")
        log.info("Comparação com ordens intuitivas (mesmos chamados, mesmo início):")
        comparacao = comparar_estrategias(entrada.chamados, entrada.turno_inicio)
        for linha in tabela_comparativa(comparacao):
            log.info("  %s", linha)

    # ----------------------------------------------------------- RESUMO
    secao("RESUMO DO TURNO")
    necessarios = particao.num_tecnicos + (1 if entrada.chamados else 0)
    log.info("Técnicos para as janelas de manutenção : %d (ótimo — profundidade %d)",
             particao.num_tecnicos, particao.profundidade)
    if entrada.chamados:
        log.info("Técnico de plantão para a fila         : 1 (ordem EDF, atraso máximo %s)",
                 duracao_legivel(edf.atraso_maximo) if edf.atraso_maximo else "0")
    log.info("Total necessário                       : %d | disponível: %d", necessarios, entrada.equipe)
    if entrada.equipe >= necessarios:
        log.info("Situação: equipe SUFICIENTE (%d técnico(s) de folga/reserva)", entrada.equipe - necessarios)
    else:
        log.warning("Situação: equipe INSUFICIENTE — faltam %d técnico(s); alguma janela terá de ser "
                    "renegociada ou a fila ficará sem plantão", necessarios - entrada.equipe)

    return {
        "interval_partitioning": {
            "tecnicos": particao.num_tecnicos,
            "profundidade": particao.profundidade,
            "otimo": particao.otimo,
            "atribuicao": {
                f"tecnico_{t}": [j.id for j in js] for t, js in sorted(particao.atribuicao.items())
            },
        },
        "minimizing_lateness": {
            "estrategia": edf.estrategia,
            "atraso_maximo_min": edf.atraso_maximo,
            "limite_inferior_min": max(0, limite),
            "fora_do_sla": [a.chamado.id for a in edf.atrasados],
            "ordem": [
                {
                    "chamado": a.chamado.id,
                    "inicio": min_para_hm(a.inicio),
                    "fim": min_para_hm(a.fim),
                    "prazo": min_para_hm(a.chamado.prazo),
                    "atraso_min": a.atraso,
                }
                for a in edf.atendimentos
            ],
            "comparacao": [
                {"estrategia": e.estrategia, "atraso_maximo_min": e.atraso_maximo, "fora_do_sla": len(e.atrasados)}
                for e in comparacao
            ],
        },
        "equipe": {"necessaria": necessarios, "disponivel": entrada.equipe, "suficiente": entrada.equipe >= necessarios},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Escalonador de help desk com algoritmos gulosos.")
    parser.add_argument("entrada", help="arquivo JSON com turno, janelas de manutenção e chamados")
    parser.add_argument("--debug", action="store_true", help="mostra o estado interno (heap, ordenações)")
    parser.add_argument("--json", metavar="ARQUIVO", help="grava o resultado estruturado em JSON")
    parser.add_argument("--sem-comparacao", action="store_true", help="não simula FIFO/SPT/prioridade")
    args = parser.parse_args(argv)

    # permite `python main.py ... | head` sem traceback de Broken pipe (não existe no Windows)
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(name)-4s| %(message)s",
        stream=sys.stdout,
    )

    try:
        entrada = carregar(args.entrada)
    except (OSError, ValueError, KeyError) as e:
        log.error("não foi possível ler a entrada: %s", e)
        return 2

    resultado = executar(entrada, comparar=not args.sem_comparacao)

    if args.json:
        Path(args.json).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("")
        log.info("Resultado gravado em %s", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
