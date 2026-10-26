import logging
import pandas as pd
from sqlalchemy import text
from config import get_db_engine

COLUNAS_OBRIGATORIAS = [
    "id_cliente", "razao_social", "vendedor_responsavel", "ano_mes",
    "total_pedidos", "faturamento", "dias_sem_movimentacao",
]

QUERY = text("""
WITH base AS (
    SELECT
        c.CTE_ID                                AS CTE_ID,       
        c.razao_social                                 AS razao_social,     
        c.vendedor                                     AS vendedor_responsavel, 
        DATEFROMPARTS(YEAR(e.data_emissao), MONTH(e.data_emissao), 1) AS ano_mes,
        e.id_pedido                                    AS id_pedido,        
        e.FREVAL                           AS FREVAL,     
        e.data_emissao                                 AS data_emissao      
    FROM dbo.cte e                                                            
    JOIN dbo.clientes c ON c.id_cliente = e.id_cliente                       
    WHERE e.data_emissao >= DATEADD(MONTH, -12,
              DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1))
      AND e.situacao NOT IN ('CANCELADO', 'DENEGADO')                         
)
SELECT
    id_cliente, razao_social, vendedor_responsavel, ano_mes,
    COUNT(DISTINCT id_pedido)  AS total_pedidos,
    SUM(valor_frete)           AS faturamento,
    DATEDIFF(DAY,
             MAX(MAX(data_emissao)) OVER (PARTITION BY id_cliente),
             CAST(GETDATE() AS date)) AS dias_sem_movimentacao
FROM base
GROUP BY id_cliente, razao_social, vendedor_responsavel, ano_mes
""")


def carregar_dados_comerciais() -> pd.DataFrame:
    engine = get_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(QUERY, conn)

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes no resultado da query: {faltando}")

    df["ano_mes"] = pd.to_datetime(df["ano_mes"])
    df["faturamento"] = pd.to_numeric(df["faturamento"], errors="coerce").fillna(0.0).astype(float)
    df["total_pedidos"] = pd.to_numeric(df["total_pedidos"], errors="coerce").fillna(0).astype(int)
    df["dias_sem_movimentacao"] = (pd.to_numeric(df["dias_sem_movimentacao"], errors="coerce")
                                   .fillna(0).astype(int))
    df["razao_social"] = df["razao_social"].fillna("(sem nome)").astype(str).str.strip()
    df["vendedor_responsavel"] = df["vendedor_responsavel"].fillna("Sem vendedor")

    ruins = (df["faturamento"] < 0) | (df["ano_mes"] > pd.Timestamp.today())
    if ruins.any():
        logging.warning(f"{int(ruins.sum())} linhas descartadas por qualidade (valor negativo/data futura).")
        df = df[~ruins]
    return df
