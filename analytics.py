from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, linregress

JANELA_MESES = 12
MIN_MESES_HISTORICO = 6     
TOLERANCIA_RUIDO = 0.02      

PESOS = {
    "queda": 0.25,
    "tendencia": 0.20,
    "frequencia": 0.20,
    "recorrencia": 0.10,
    "participacao": 0.10,
    "risco_perda": 0.15,
}

CURVAS = {
    "queda": ([0, 10, 20, 30, 40], [0, 25, 60, 85, 100]),      
    "slope": ([0, 2, 4, 7, 10], [0, 20, 50, 85, 100]),         
    "meses_queda": ([0, 1, 2, 4, 6], [0, 10, 30, 70, 100]),     
    "frequencia": ([1, 2, 4, 8], [0, 25, 60, 100]),            
    "recorrencia": ([0, 1, 2, 4, 6], [0, 25, 50, 85, 100]),     
    "participacao": ([0, 1, 5, 10], [0, 20, 60, 100]),         
}

PISO_ATENCAO = 61
PISO_CRITICO = 81

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

CORES = {
    "Saudável": "#28a745", "Monitorar": "#ffc107", "Atenção": "#fd7e14",
    "Crítico": "#dc3545", "Novo": "#6c757d",
}

def calcular_tendencia_slope(serie_valores: np.ndarray) -> float:
    if len(serie_valores) < 2 or np.all(serie_valores == serie_valores[0]):
        return 0.0
    x = np.arange(len(serie_valores))
    slope, *_ = linregress(x, serie_valores)
    return float(slope)


def _pontuar(x: float, curva: tuple) -> float:
    return float(np.interp(x, curva[0], curva[1]))


def _var(atual: float, anterior: float) -> float:
    if anterior > 0:
        return atual / anterior - 1.0
    return 1.0 if atual > 0 else 0.0


def _status(score: float) -> str:
    if score <= 30:
        return "Saudável"
    if score <= 60:
        return "Monitorar"
    if score <= 80:
        return "Atenção"
    return "Crítico"


def _sequencia(s: np.ndarray, sentido: int) -> int:
    """Meses consecutivos de queda (sentido=-1) ou alta (+1), contando do fim.
    Variações de até 2% na direção contrária não quebram a sequência."""
    n = 0
    for t in range(len(s) - 1, 0, -1):
        cur, prev = s[t], s[t - 1]
        if sentido < 0:
            if cur < prev:
                n += 1
            elif cur > prev * (1 + TOLERANCIA_RUIDO):
                break
        else:
            if cur > prev:
                n += 1
            elif cur < prev * (1 - TOLERANCIA_RUIDO):
                break
    return n


def _fmt_int(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def _fmt_periodo(p: pd.Period) -> str:
    return f"{MESES_PT[p.month - 1]}/{p.year}"


def _ritmo(gap: float) -> str:
    if gap < 1.5:
        return "embarques praticamente diários"
    return f"cerca de 1 embarque a cada {gap:.0f} dias"


def _pct_br(x: float) -> str:
    return f"{x:.1%}".replace(".", ",")


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural

def _analisar_cliente(p, f, dias_inativo, share, periodos) -> dict | None:
    n = len(p)
    ativos = np.flatnonzero((p > 0) | (f > 0))
    if ativos.size == 0:
        return None 

    primeiro = int(ativos[0])
    meses_hist = n - primeiro
    evolucao = " | ".join(
        f"{MESES_PT[per.month - 1]}={_fmt_int(v)}" for per, v in zip(periodos[-6:], p[-6:])
    )

    base = {
        "faturamento_12m": float(f.sum()),
        "fat_ult_90d": float(f[-3:].sum()),
        "dias_inativo": int(dias_inativo),
        "share_receita_pct": round(share * 100, 2),
        "evolucao_pedidos": evolucao,
    }

    if meses_hist < MIN_MESES_HISTORICO:
        return {
            **base, "score": 0, "status": "Novo", "badge_color": CORES["Novo"],
            "var_pct_90d": 0.0, "var_pct_90d_fat": 0.0, "queda_acum_pct": 0.0,
            "meses_em_queda": 0, "inicio_tendencia": "", "tipo_queda": "sem histórico",
            "alertas": "", "oportunidade": "", "acao_imediata": False,
            "impacto_mensal": 0.0, "exposicao": 0.0, "piso_aplicado": "",
            **{f"score_{k}": 0.0 for k in PESOS},
            "diagnostico": f"Cliente com {meses_hist} meses de histórico; "
                           "ainda sem base para análise de tendência.",
            "acao_recomendada": "Acompanhar o desenvolvimento do relacionamento.",
        }

    s = p[primeiro:].astype(float)       
    sf = f[primeiro:].astype(float)

    var_ped = _var(p[-3:].sum(), p[-6:-3].sum())
    var_fat = _var(f[-3:].sum(), f[-6:-3].sum())

    m2 = pd.Series(s).rolling(2).mean().dropna().to_numpy()
    pico = float(m2.max()) if m2.size else float(s.max())
    atual = float(s[-2:].mean())
    queda_acum = max(0.0, 1 - atual / pico) if pico > 0 else 0.0

    inicio = ""
    if queda_acum >= 0.10:
        pos = np.flatnonzero(s >= 0.97 * pico)
        pico_pos = int(pos[-1]) if pos.size else 0
        if pico_pos < len(s) - 1:
            inicio = _fmt_periodo(periodos[primeiro + pico_pos + 1])

    meses_queda = max(_sequencia(s, -1), _sequencia(sf, -1))
    meses_alta = _sequencia(s, +1)

    def _queda_pct_mes(serie):
        ult = serie[-6:]
        media = ult.mean()
        if media <= 0:
            return 0.0
        return max(0.0, -calcular_tendencia_slope(ult) / media * 100)

    slope_pct = (_queda_pct_mes(p) + _queda_pct_mes(f)) / 2

    ped_ativos = p[p > 0]
    media_ped = float(ped_ativos.mean()) if ped_ativos.size else 1.0
    gap_esperado = float(np.clip(30.0 / max(media_ped, 1.0), 1.0, 30.0))
    razao_gap = dias_inativo / gap_esperado
    ativo_6m = bool(p[-6:].sum() > 0)

    baseline = float(np.percentile(s, 75))
    ult6 = s[-6:]
    abaixo = int((ult6 < 0.9 * baseline).sum())
    tau = kendalltau(np.arange(6), ult6).statistic if np.ptp(ult6) > 0 else 0.0
    tau = 0.0 if tau is None or np.isnan(tau) else float(tau)
    recuperando = bool(s[-2:].mean() >= 0.9 * baseline)

    if queda_acum < 0.10 and var_ped > -0.10:
        tipo = "sem queda"
    elif (abaixo >= 3 or meses_queda >= 4) and tau <= -0.5 and not recuperando:
        tipo = "estrutural"
    elif abaixo <= 2 and recuperando:
        tipo = "pontual"
    elif abaixo <= 2:
        tipo = "recente"
    else:
        tipo = "oscilante"

    q_ped = _pontuar(max(0.0, -var_ped) * 100, CURVAS["queda"])
    q_fat = _pontuar(max(0.0, -var_fat) * 100, CURVAS["queda"])
    q_acum = _pontuar(queda_acum * 100, CURVAS["queda"])
    c_queda = max(0.6 * q_ped + 0.4 * q_fat, 0.9 * q_acum)

    c_tend = (0.6 * _pontuar(slope_pct, CURVAS["slope"])
              + 0.4 * _pontuar(meses_queda, CURVAS["meses_queda"]))

    c_freq = _pontuar(razao_gap, CURVAS["frequencia"]) if dias_inativo >= 7 else 0.0

    ativos_ult6 = int((p[-6:] > 0).sum())
    ativos_prev6 = int((p[-12:-6] > 0).sum())
    c_recor = (_pontuar(6 - ativos_ult6, CURVAS["recorrencia"])
               if ativos_prev6 >= 4 else 0.0)   

    deterioracao = (c_queda + c_tend + c_freq) / 3
    c_part = _pontuar(share * 100, CURVAS["participacao"]) * deterioracao / 100

    c_risco = 0.5 * q_acum + 0.3 * q_fat + 0.2 * c_freq

    comps = {"queda": c_queda, "tendencia": c_tend, "frequencia": c_freq,
             "recorrencia": c_recor, "participacao": c_part, "risco_perda": c_risco}
    score = sum(PESOS[k] * v for k, v in comps.items())

    piso, motivo = 0, ""

    def _piso(valor, texto):
        nonlocal piso, motivo
        if valor > piso:
            piso, motivo = valor, texto

    if tipo == "estrutural" and queda_acum >= 0.20:
        _piso(PISO_CRITICO, "queda estrutural >= 20%")
    elif tipo == "estrutural" and queda_acum >= 0.10:
        _piso(PISO_ATENCAO, "queda estrutural >= 10%")
    if share >= 0.10 and var_fat <= -0.20:
        _piso(PISO_CRITICO, "cliente >10% da receita com queda >20%")
    if ativo_6m and dias_inativo >= 30 and razao_gap >= 3:
        _piso(PISO_CRITICO, "30+ dias sem embarque")
    elif ativo_6m and dias_inativo >= 15 and razao_gap >= 3:
        _piso(PISO_ATENCAO, "15+ dias sem embarque")

    score = int(round(min(100, max(score, piso))))
    status = _status(score)

    fat_media_6m = float(f[-6:].mean())
    impacto_mensal = max(0.0, float(f[-6:-3].mean() - f[-3:].mean()))
    exposicao = score / 100 * fat_media_6m  

    alertas = []
    if share >= 0.10 and (var_fat < -0.10 or var_ped < -0.10):
        alertas.append(f"Cliente representa {_pct_br(share)} da receita e está em queda.")
    if ativo_6m and dias_inativo >= 15:
        alertas.append(f"Cliente está há {dias_inativo} dias sem embarques.")
    if var_ped < -0.20 or var_fat < -0.20:
        alertas.append(f"Queda superior a 20% em 90 dias "
                       f"(pedidos {var_ped:+.0%}, faturamento {var_fat:+.0%}).")
    if meses_queda >= 6:
        alertas.append(f"Tendência negativa por {meses_queda} meses consecutivos.")

    oportunidade = ""
    if status in ("Saudável", "Monitorar"):
        recup = bool(len(s) >= 6 and s[-6:-2].min() < 0.8 * baseline and recuperando)
        acima_historico = bool(s[-3:].mean() > 1.1 * baseline)
        if var_ped >= 0.25 and meses_alta >= 2 and acima_historico:
            oportunidade = "Crescimento acelerado"
        elif recup:
            oportunidade = "Cliente recuperado"
        elif len(s) >= 4 and s[-1] > 0 and s[-1] >= 1.3 * s[-4:-1].mean():
            oportunidade = "Aumento recente de volume"

    frases = []
    if tipo == "estrutural":
        desde = f" (desde {inicio})" if inicio else ""
        frases.append(f"Queda contínua há {meses_queda} meses{desde}. "
                      f"Redução acumulada de {queda_acum:.0%} nos pedidos sobre o pico, "
                      "sem sinais de recuperação.")
    elif tipo == "oscilante":
        frases.append(f"Volume oscilante, {queda_acum:.0%} abaixo do pico, sem direção clara.")
    elif tipo == "recente":
        frases.append(f"Redução recente de {queda_acum:.0%} sobre o pico; "
                      "ainda sem tendência consolidada.")
    elif tipo == "pontual":
        frases.append("Queda pontual: houve meses abaixo do padrão, "
                      "mas o volume já voltou ao patamar histórico.")
    if ativo_6m and dias_inativo >= 15 and razao_gap >= 3:
        frases.append(f"Sem embarques há {dias_inativo} dias, muito acima do ritmo "
                      f"normal do cliente ({_ritmo(gap_esperado)}).")
    if var_fat < var_ped - 0.10 and var_fat < -0.10:
        frases.append(f"O faturamento caiu mais que os pedidos ({var_fat:+.0%} vs "
                      f"{var_ped:+.0%}): possível perda de carga de maior valor "
                      "ou revisão de tabela.")
    if oportunidade:
        frases.append(f"{oportunidade}: pedidos {var_ped:+.0%} nos últimos 90 dias.")
    if not frases:
        frases.append("Movimentação operacional dentro do padrão histórico.")
    diagnostico = " ".join(frases)

    acoes = []
    if status == "Crítico":
        acoes += ["Contato comercial imediato", "Reunião executiva",
                  "Validar concorrência", "Revisar contrato e tabela de frete"]
    elif status == "Atenção":
        acoes += ["Contato comercial em até 7 dias",
                  "Entender mudança na rotina de embarque do cliente",
                  "Revisar SLA e ocorrências recentes"]
    elif status == "Monitorar":
        acoes += ["Acompanhar na próxima semana antes de acionar o cliente"]
    if ativo_6m and dias_inativo >= 15 and razao_gap >= 3:
        acoes.append("Falar com a expedição do cliente sobre a pausa nos embarques")
    if var_fat < var_ped - 0.10 and var_fat < -0.10:
        acoes.append("Revisar tabela de frete do cliente")
    if oportunidade == "Cliente recuperado":
        acoes.append("Reforçar o relacionamento para consolidar a retomada do volume")
    elif oportunidade:
        acoes.append("Apresentar proposta de rotas complementares / volume adicional")
    if not acoes:
        acoes.append("Manter acompanhamento de rotina na carteira.")
    acoes = list(dict.fromkeys(acoes))

    acao_imediata = status == "Crítico" or (status == "Atenção" and dias_inativo >= 15)

    return {
        **base,
        "score": score, "status": status, "badge_color": CORES[status],
        "var_pct_90d": round(var_ped * 100, 1),
        "var_pct_90d_fat": round(var_fat * 100, 1),
        "queda_acum_pct": round(queda_acum * 100, 1),
        "meses_em_queda": meses_queda,
        "inicio_tendencia": inicio,
        "tipo_queda": tipo,
        "alertas": " | ".join(alertas),
        "oportunidade": oportunidade,
        "acao_imediata": acao_imediata,
        "impacto_mensal": round(impacto_mensal, 2),
        "exposicao": round(exposicao, 2),
        "piso_aplicado": motivo,
        **{f"score_{k}": round(v, 1) for k, v in comps.items()},
        "diagnostico": diagnostico,
        "acao_recomendada": "; ".join(acoes),
    }

def processar_inteligencia_comercial(
    df_raw: pd.DataFrame,
    mes_referencia: pd.Timestamp | None = None,
    excluir_mes_corrente: bool = True,
) -> pd.DataFrame:
    """Analisa todos os clientes.

    excluir_mes_corrente=True ignora o mês em andamento nas séries (ele é
    parcial e pareceria uma queda falsa). Os dias sem movimentação continuam
    sendo calculados até hoje.
    """
    df = df_raw.copy()
    df["periodo"] = pd.to_datetime(df["ano_mes"]).dt.to_period("M")

    meta = (df.sort_values("periodo")
              .groupby("id_cliente")
              .last()[["razao_social", "vendedor_responsavel", "dias_sem_movimentacao"]])

    hoje = pd.Timestamp(mes_referencia) if mes_referencia is not None else pd.Timestamp.today()
    ultimo = hoje.to_period("M") - (1 if excluir_mes_corrente else 0)
    periodos = pd.period_range(end=ultimo, periods=JANELA_MESES, freq="M")

    dfj = df[df["periodo"].isin(periodos)]

    def _grade(col):  
        return (dfj.pivot_table(index="id_cliente", columns="periodo", values=col,
                                aggfunc="sum", fill_value=0)
                   .reindex(columns=periodos, fill_value=0))

    ped, fat = _grade("total_pedidos"), _grade("faturamento")
    total_fat = float(np.clip(fat.to_numpy(), 0, None).sum()) or 1.0

    linhas = []
    for id_cliente in ped.index:
        p = ped.loc[id_cliente].to_numpy(dtype=float)
        f = fat.loc[id_cliente].to_numpy(dtype=float)
        share = max(0.0, float(f.sum())) / total_fat
        dias = meta.loc[id_cliente, "dias_sem_movimentacao"]
        dias = 0 if pd.isna(dias) else int(dias)

        r = _analisar_cliente(p, f, dias, share, periodos)
        if r is None:
            continue
        r.update(id_cliente=id_cliente,
                 razao_social=meta.loc[id_cliente, "razao_social"],
                 vendedor=meta.loc[id_cliente, "vendedor_responsavel"])
        linhas.append(r)

    out = pd.DataFrame(linhas)
    if out.empty:
        return out
    return out.sort_values(["exposicao", "score"], ascending=False).reset_index(drop=True)

_CAUSAS = {
    "queda": "a redução progressiva do volume de pedidos e do faturamento nos últimos 90 dias",
    "tendencia": "a tendência negativa persistente dos pedidos ao longo dos últimos meses",
    "frequencia": "o aumento do tempo sem embarques em relação ao ritmo normal dos clientes",
    "recorrencia": "a perda de recorrência de embarques de clientes antes regulares",
    "participacao": "a deterioração de clientes com alta participação na receita",
    "risco_perda": "sinais combinados de perda de volume e valor em relação ao pico",
}


def gerar_resumo_executivo(df: pd.DataFrame) -> str:
    analisados = df[df["status"] != "Novo"]
    total = len(df)
    crit = int((df["status"] == "Crítico").sum())
    aten = int((df["status"] == "Atenção").sum())
    moni = int((df["status"] == "Monitorar").sum())
    novos = int((df["status"] == "Novo").sum())
    imediata = int(df["acao_imediata"].sum())
    oport = int((df["oportunidade"] != "").sum())

    partes = [f"Foram analisados {total} clientes."]
    partes.append(f"{crit} {_plural(crit, 'cliente foi classificado', 'clientes foram classificados')} "
                  f"como {_plural(crit, 'crítico', 'críticos')}.")
    partes.append(f"{aten} {_plural(aten, 'cliente foi classificado', 'clientes foram classificados')} "
                  "como atenção.")
    partes.append(f"{moni} {_plural(moni, 'cliente está', 'clientes estão')} em monitoramento.")
    if novos:
        partes.append(f"{novos} {_plural(novos, 'cliente tem', 'clientes têm')} histórico "
                      "insuficiente e não entrou na análise de tendência.")

    risco = analisados[analisados["status"].isin(["Crítico", "Atenção"])]
    if not risco.empty:
        medias = {k: risco[f"score_{k}"].mean() * PESOS[k] for k in PESOS}
        causa = max(medias, key=medias.get)
        partes.append(f"A principal causa observada foi {_CAUSAS[causa]}.")
    partes.append(f"{imediata} {_plural(imediata, 'cliente exige', 'clientes exigem')} ação imediata.")
    if oport:
        partes.append(f"Foram identificadas {oport} oportunidades comerciais "
                      "(crescimento, recuperação ou aumento recente de volume).")
    return "\n".join(partes)
