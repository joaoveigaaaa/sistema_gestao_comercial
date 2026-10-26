import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()  


def get_db_engine():
    """Engine SQLAlchemy para SQL Server (usar usuário SOMENTE LEITURA)."""
    dialeto = os.getenv("DB_DRIVER", "mssql+pyodbc")
    odbc = os.getenv("DB_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
    user = quote_plus(os.getenv("DB_USER", ""))
    senha = quote_plus(os.getenv("DB_PASSWORD", ""))     
    host = os.getenv("DB_HOST", "localhost")
    porta = os.getenv("DB_PORT", "1433")
    banco = os.getenv("DB_DATABASE", "")

    url = (f"{dialeto}://{user}:{senha}@{host}:{porta}/{banco}"
           f"?driver={quote_plus(odbc)}&TrustServerCertificate=yes")
    return create_engine(url, pool_pre_ping=True)
