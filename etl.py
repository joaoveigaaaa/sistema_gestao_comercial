import pandas as pd
from config import get_db_engine

def carregar_dados_comerciais() -> pd.DataFrame:
    engine = get_db_engine()
    query = "SELECT * FROM clientes"
    df = pd.read_sql(query, engine)

    df['faturamento'] = df['faturamento'].astype(float)
    df['total_pedidos'] = df['total_pedidos'].astype(int)
    df['dias_sem_movimentacao'] = df['dias_sem_movimentacao'].astype(int)

    return df