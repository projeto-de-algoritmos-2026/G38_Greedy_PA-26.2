"""Conversão entre "HH:MM" e minutos desde a meia-noite.

Todo o programa trabalha internamente com inteiros (minutos). Isso evita
aritmética de datetime e deixa as comparações dos algoritmos triviais.
"""

MINUTOS_POR_DIA = 24 * 60


def hm_para_min(texto: str) -> int:
    """'08:30' -> 510."""
    try:
        horas, minutos = texto.strip().split(":")
        h, m = int(horas), int(minutos)
    except (ValueError, AttributeError):
        raise ValueError(f"horário inválido: {texto!r} (esperado HH:MM)") from None
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"horário fora do intervalo: {texto!r}")
    return h * 60 + m


def min_para_hm(total: int) -> str:
    """510 -> '08:30'. Valores além de 24h ganham o sufixo (+Nd)."""
    dias, resto = divmod(total, MINUTOS_POR_DIA)
    h, m = divmod(resto, 60)
    sufixo = f" (+{dias}d)" if dias else ""
    return f"{h:02d}:{m:02d}{sufixo}"


def duracao_legivel(minutos: int) -> str:
    """90 -> '1h30', 60 -> '1h', 25 -> '25min'."""
    h, m = divmod(minutos, 60)
    if h and m:
        return f"{h}h{m:02d}"
    if h:
        return f"{h}h"
    return f"{m}min"
