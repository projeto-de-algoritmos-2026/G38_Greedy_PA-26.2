"""Entidades do domínio e leitura/validação do arquivo de entrada (JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .tempo import hm_para_min


@dataclass(frozen=True)
class JanelaManutencao:
    """Atividade com horário fixo, acordado previamente com a área solicitante.

    Exige um técnico dedicado do início ao fim. Entrada do Interval Partitioning.
    """

    id: str
    descricao: str
    inicio: int  # minutos desde 00:00
    fim: int

    @property
    def duracao(self) -> int:
        return self.fim - self.inicio


@dataclass(frozen=True)
class Chamado:
    """Ticket na fila do técnico de plantão. Entrada do Minimizing Lateness.

    `prazo` é o instante em que o SLA (prazo contratual de resolução) expira.
    `abertura` é apenas informativo — aparece no log para contextualizar o prazo.
    """

    id: str
    descricao: str
    prioridade: str
    duracao: int  # minutos estimados de atendimento
    prazo: int  # minuto do dia em que o SLA expira
    abertura: str = ""


@dataclass
class Entrada:
    turno_inicio: int
    turno_fim: int
    equipe: int
    janelas: list[JanelaManutencao]
    chamados: list[Chamado]


def _exigir(cond: bool, mensagem: str) -> None:
    if not cond:
        raise ValueError(mensagem)


def carregar(caminho: str | Path) -> Entrada:
    """Lê e valida o JSON de entrada. Lança ValueError com mensagem clara se inválido."""
    with open(caminho, encoding="utf-8") as f:
        bruto = json.load(f)

    turno = bruto.get("turno", {})
    turno_inicio = hm_para_min(turno.get("inicio", "08:00"))
    turno_fim = hm_para_min(turno.get("fim", "18:00"))
    _exigir(turno_fim > turno_inicio, "turno.fim deve ser depois de turno.inicio")

    equipe = int(bruto.get("equipe_disponivel", 0))
    _exigir(equipe >= 0, "equipe_disponivel não pode ser negativa")

    janelas: list[JanelaManutencao] = []
    ids: set[str] = set()
    for item in bruto.get("janelas_manutencao", []):
        j = JanelaManutencao(
            id=str(item["id"]),
            descricao=str(item.get("descricao", "")),
            inicio=hm_para_min(item["inicio"]),
            fim=hm_para_min(item["fim"]),
        )
        _exigir(j.fim > j.inicio, f"janela {j.id}: fim deve ser depois do início")
        _exigir(j.id not in ids, f"id duplicado: {j.id}")
        ids.add(j.id)
        janelas.append(j)

    chamados: list[Chamado] = []
    for item in bruto.get("chamados", []):
        c = Chamado(
            id=str(item["id"]),
            descricao=str(item.get("descricao", "")),
            prioridade=str(item.get("prioridade", "P3")),
            duracao=int(item["duracao_min"]),
            prazo=hm_para_min(item["prazo"]),
            abertura=str(item.get("abertura", "")),
        )
        _exigir(c.duracao > 0, f"chamado {c.id}: duracao_min deve ser positiva")
        _exigir(c.id not in ids, f"id duplicado: {c.id}")
        ids.add(c.id)
        chamados.append(c)

    return Entrada(turno_inicio, turno_fim, equipe, janelas, chamados)
