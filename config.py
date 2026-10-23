import os 
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

def get_db_engine():
    dialeto = os.getenv("DB_DRIVER")
    odbc_driver = os.getenv("DB_ODBC_DRIVER")
    user = quote_plus(os.getenv("DB_USER"))
    senha = quote_plus(os.getenv("DB_PASSWORD"))

    host = os.getenv("DB_HOST")
    porta = os.getenv("DB_PORT")
    banco = os.getenv("DB_NAME")

    url = f"{dialeto}://{user}:{senha}@{host}:{porta}/{banco}"
    return create_engine(url, pool_pre_ping=True)
