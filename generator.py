import datetime
from jinja2 import Template
from weasyprint import HTML

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; color: #333; margin: 20px; }
        .header { background: #1a252f; color: #fff; padding: 15px; text-align: center; border-radius: 4px; }
        .kpi-container { display: flex; justify-content: space-between; margin-top: 15px; }
        .kpi-card { background: #f8f9fa; border: 1px solid #ddd; padding: 10px; width: 22%; text-align: center; border-radius: 4px; }
        .number { font-size: 20px; font-weight: bold; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 11px; }
        th { background: #2c3e50; color: white; padding: 8px; text-align: left; }
        td { border-bottom: 1px solid #ddd; padding: 8px; }
        .badge { color: white; padding: 3px 6px; border-radius: 3px; font-weight: bold; font-size: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>Relatório de Inteligência Comercial</h2>
        <p>Análise Preditiva e Prescritiva | Gerado em: {{ data_geracao }}</p>
    </div>

    <div class="kpi-container">
        <div class="kpi-card">Total Analisado<div class="number">{{ total_clientes }}</div></div>
        <div class="kpi-card">Críticos 🔴<div class="number" style="color:#dc3545;">{{ qtd_criticos }}</div></div>
        <div class="kpi-card">Atenção 🟠<div class="number" style="color:#fd7e14;">{{ qtd_atencao }}</div></div>
        <div class="kpi-card">Saudáveis 🟢<div class="number" style="color:#28a745;">{{ qtd_saudaveis }}</div></div>
    </div>

    <h3>🚨 Ranking de Prioridades Comerciais</h3>
    <table>
        <thead>
            <tr>
                <th>Cliente</th>
                <th>Status / Score</th>
                <th>Var. 90d</th>
                <th>Inatividade</th>
                <th>Diagnóstico</th>
                <th>Ação Recomendada</th>
            </tr>
        </thead>
        <tbody>
            {% for item in ranking %}
            <tr>
                <td><b>{{ item.razao_social }}</b><br><small>{{ item.vendedor }}</small></td>
                <td><span class="badge" style="background-color: {{ item.badge_color }};">{{ item.status }}</span> ({{ item.score }})</td>
                <td style="color: {% if item.var_pct_90d < 0 %}red{% else %}green{% endif %};"><b>{{ item.var_pct_90d }}%</b></td>
                <td>{{ item.dias_inativo }} dias</td>
                <td>{{ item.diagnostico }}</td>
                <td><b>{{ item.acao_recomendada }}</b></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def gerar_pdf_relatorio(df_resumo, output_pdf="Relatorio_Inteligencia_Comercial.pdf"):
    total_clientes = len(df_resumo)
    qtd_criticos = len(df_resumo[df_resumo['status'] == 'Crítico'])
    qtd_atencao = len(df_resumo[df_resumo['status'] == 'Atenção'])
    qtd_saudaveis = len(df_resumo[df_resumo['status'] == 'Saudável'])

    ranking = df_resumo[df_resumo['status'].isin(['Crítico', 'Atenção'])].sort_values(
        by=['score', 'faturamento_12m'], ascending=[False, False]
    ).head(15).to_dict(orient='records')

    template = Template(HTML_TEMPLATE)
    html_out = template.render(
        data_geracao=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        total_clientes=total_clientes,
        qtd_criticos=qtd_criticos,
        qtd_atencao=qtd_atencao,
        qtd_saudaveis=qtd_saudaveis,
        ranking=ranking
    )

    HTML(string=html_out).write_pdf(output_pdf)
    return output_pdf