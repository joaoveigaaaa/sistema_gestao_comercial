from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, linregress

def calcular_tendencia_slope(serie_valores: np.ndarray) -> float:

    if len(serie_valores) < 2 or np.all(serie_valores == serie_valores[0]):
        return 0.0
    x = np.arange(len(serie_valores))
    slope, _, _, _, _ = linregress(x, serie_valores)
    return float(slope)

def processar_inteligencia_comercial(df_raw: pd.DataFrame) -> pd.DataFrame:
    resultados = []

    for id_cliente, grupo in df_raw.groupby('id_cliente'):
        grupo = grupo.sort_values('ano_mes')
        
        razao_social = grupo['razao_social'].iloc[-1]
        vendedor = grupo['vendedor_responsavel'].iloc[-1]
        dias_inativo = grupo['dias_sem_movimentacao'].iloc[-1]
        
        fat_historico = grupo['faturamento'].values
        fat_6m = fat_historico[-6:] if len(fat_historico) >= 6 else fat_historico
        fat_total_12m = fat_historico.sum()

        slope = calcular_tendencia_slope(fat_6m)
        media_fat_6m = fat_6m.mean() if len(fat_6m) > 0 else 0

        fat_ult_90d = fat_historico[-3:].sum() if len(fat_historico) >= 3 else fat_historico.sum()
        fat_ant_90d = fat_historico[-6:-3].sum() if len(fat_historico) >= 6 else fat_ult_90d
        
        if fat_ant_90d > 0:
            var_pct_90d = (fat_ult_90d - fat_ant_90d) / fat_ant_90d
        else:
            var_pct_90d = 0.0

        sub_slope = min(100.0, max(0.0, (-slope / (media_fat_6m + 1.0)) * 100.0)) if media_fat_6m > 0 else 0.0
        
        sub_queda = min(100.0, max(0.0, -var_pct_90d * 100.0))
        
        sub_inativ = min(100.0, (dias_inativo / 30.0) * 100.0)
   
        score = int(round((sub_slope * 0.35) + (sub_queda * 0.40) + (sub_inativ * 0.25)))
        score = max(0, min(100, score)) 
 
        if score <= 30:
            status, badge_color = "Saudável", "#28a745"
        elif score <= 60:
            status, badge_color = "Monitorar", "#ffc107"
        elif score <= 80:
            status, badge_color = "Atenção", "#fd7e14"
        else:
            status, badge_color = "Crítico", "#dc3545"

        if var_pct_90d < -0.20 and slope < 0:
            diagnostico = "Queda estrutural contínua nos últimos 6 meses."
            acao = "Agendar reunião presencial urgente. Auditar tabela de frete do concorrente e SLA."
        elif dias_inativo > 15:
            diagnostico = f"Cliente inativo há {dias_inativo} dias sem emissões de CT-e."
            acao = "Contato imediato com o setor de expedição para identificar alteração na rotina de embarque."
        elif var_pct_90d > 0.25:
            diagnostico = "Crescimento acelerado no volume expedido."
            acao = "Apresentar proposta para rotas complementares e contratação de frota dedicada."
        else:
            diagnostico = "Movimentação operacional dentro do padrão histórico."
            acao = "Manter acompanhamento de rotina na carteira."

        resultados.append({
            'id_cliente': id_cliente,
            'razao_social': razao_social,
            'vendedor': vendedor,
            'score': score,
            'status': status,
            'badge_color': badge_color,
            'faturamento_12m': fat_total_12m,
            'fat_ult_90d': fat_ult_90d,
            'var_pct_90d': round(var_pct_90d * 100.0, 1),
            'dias_inativo': dias_inativo,
            'diagnostico': diagnostico,
            'acao_recomendada': acao
        })

    return pd.DataFrame(resultados)