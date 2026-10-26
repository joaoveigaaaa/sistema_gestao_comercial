import datetime

from jinja2 import Environment

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: A4 landscape; margin: 12mm; }
  body { font-family: Arial, Helvetica, sans-serif; color: #333; font-size: 11px; }
  .header { background: #1a252f; color: #fff; padding: 14px; text-align: center; }
  .header h2 { margin: 0 0 4px 0; }
  .resumo { background: #f8f9fa; border-left: 4px solid #1a252f; padding: 10px 14px; margin: 14px 0; line-height: 1.5; }
  table.kpi { width: 100%; border-spacing: 8px; margin: 0 -8px; }
  table.kpi td { background: #f8f9fa; border: 1px solid #ddd; text-align: center; padding: 8px; width: 20%; }
  .num { font-size: 20px; font-weight: bold; }
  h3 { margin: 18px 0 6px 0; color: #1a252f; }
  table.grid { width: 100%; border-collapse: collapse; font-size: 10px; }
  table.grid th { background: #2c3e50; color: #fff; padding: 6px; text-align: left; }
  table.grid td { border-bottom: 1px solid #ddd; padding: 6px; vertical-align: top; }
  .badge { color: #fff; padding: 2px 6px; border-radius: 3px; font-weight: bold; font-size: 9px; }
  .neg { color: #c0392b; } .pos { color: #1e8449; }
  small { color: #666; }
</style>
</head>
<body>
<div class="header">
  <h2>Relatório de Inteligência Comercial</h2>
  <div>Gerado em {{ data_geracao }}</div>
</div>

<div class="resumo"><b>Resumo Executivo</b><br>
{% for linha in resumo_linhas %}{{ linha }}<br>{% endfor %}
</div>

<table class="kpi"><tr>
  <td>Total analisado<div class="num">{{ total }}</div></td>
  <td>Crítico<div class="num" style="color:#dc3545;">{{ qtd.get('Crítico', 0) }}</div></td>
  <td>Atenção<div class="num" style="color:#fd7e14;">{{ qtd.get('Atenção', 0) }}</div></td>
  <td>Monitorar<div class="num" style="color:#d4a106;">{{ qtd.get('Monitorar', 0) }}</div></td>
  <td>Saudável<div class="num" style="color:#28a745;">{{ qtd.get('Saudável', 0) }}</div></td>
</tr></table>

<h3>Ranking de Prioridades Comerciais</h3>
<table class="grid">
<thead><tr><th>#</th><th>Cliente</th><th>Status / Score</th><th>Var. 90d<br>pedidos / fat.</th>
<th>Sem embarque</th><th>Diagnóstico</th><th>Ação recomendada</th></tr></thead>
<tbody>
{% for i in ranking %}
<tr>
  <td>{{ loop.index }}º</td>
  <td><b>{{ i.razao_social }}</b><br><small>{{ i.vendedor }}</small></td>
  <td><span class="badge" style="background:{{ i.badge_color }};">{{ i.status }}</span> {{ i.score }}</td>
  <td><span class="{{ 'neg' if i.var_pct_90d < 0 else 'pos' }}"><b>{{ '%+.1f'|format(i.var_pct_90d) }}%</b></span> /
      <span class="{{ 'neg' if i.var_pct_90d_fat < 0 else 'pos' }}">{{ '%+.1f'|format(i.var_pct_90d_fat) }}%</span><br>
      <small>{{ i.evolucao_pedidos }}</small></td>
  <td>{{ i.dias_inativo }} dias</td>
  <td>{{ i.diagnostico }}</td>
  <td><b>{{ i.acao_recomendada }}</b></td>
</tr>
{% endfor %}
</tbody></table>

{% if alertas %}
<h3>Alertas Estratégicos</h3>
<table class="grid"><thead><tr><th>Cliente</th><th>Alertas</th></tr></thead><tbody>
{% for i in alertas %}<tr><td><b>{{ i.razao_social }}</b></td><td>{{ i.alertas }}</td></tr>{% endfor %}
</tbody></table>
{% endif %}

{% if oportunidades %}
<h3>Oportunidades Comerciais</h3>
<table class="grid"><thead><tr><th>Cliente</th><th>Tipo</th><th>Var. 90d pedidos</th><th>Ação sugerida</th></tr></thead><tbody>
{% for i in oportunidades %}
<tr><td><b>{{ i.razao_social }}</b><br><small>{{ i.vendedor }}</small></td><td>{{ i.oportunidade }}</td>
<td class="pos">{{ '%+.1f'|format(i.var_pct_90d) }}%</td><td>{{ i.acao_recomendada }}</td></tr>
{% endfor %}
</tbody></table>
{% endif %}
</body></html>
"""

_env = Environment(autoescape=True)


def gerar_pdf_relatorio(df_resumo, output_pdf="Relatorio_Inteligencia_Comercial.pdf",
                        resumo_texto="", top_ranking=15):
    from weasyprint import HTML 

    risco = df_resumo[df_resumo["status"].isin(["Crítico", "Atenção"])]
    ranking = (risco.sort_values(["exposicao", "score"], ascending=False)
                    .head(top_ranking).to_dict(orient="records"))
    alertas = (df_resumo[df_resumo["alertas"] != ""]
               .sort_values(["exposicao", "score"], ascending=False)
               .head(15).to_dict(orient="records"))
    oportunidades = (df_resumo[df_resumo["oportunidade"] != ""]
                     .sort_values("var_pct_90d", ascending=False)
                     .head(10).to_dict(orient="records"))

    html = _env.from_string(HTML_TEMPLATE).render(
        data_geracao=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        total=len(df_resumo),
        qtd=df_resumo["status"].value_counts().to_dict(),
        resumo_linhas=[l for l in resumo_texto.split("\n") if l.strip()],
        ranking=ranking, alertas=alertas, oportunidades=oportunidades,
    )
    HTML(string=html).write_pdf(output_pdf)
    return output_pdf
