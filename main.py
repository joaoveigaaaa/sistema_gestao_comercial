import sys
import logging
import datetime
import os

from dotenv import load_dotenv
from etl import carregar_dados_comerciais
from analytics import gerar_resumo_executivo, processar_inteligencia_comercial
from generator import gerar_pdf_relatorio
from notifier import enviar_email_relatorio

load_dotenv() 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("execucao_pipeline.log", encoding="utf-8")
    ]
)

def _destinatarios() -> list[str]:

    if os.getenv("AMBIENTE","teste")  != "producao":
        teste = os.getenv("EMAIL_TESTE", "")
        return [teste] if teste else []
    return [e.strip() for e in os.getenv("EMAIL_DESTINATARIOS", "").split(",") if e.strip()]

def executar_pipeline():
    logging.info("INICIANDO MOTOR DE INTELIGÊNCIA COMERCIAL")
    
    logging.info("Passo 1/4: A extrair dados do SQL Server via ETL...")
    df_raw = carregar_dados_comerciais()
        
    if df_raw.empty:
            logging.warning("Nenhum registo retornado do banco de dados. Pipeline interrompido.")
            return
        
    logging.info(f"ETL concluído com sucesso. Registos mensais carregados: {len(df_raw)}")

    logging.info("Passo 2/4: A processar o algoritmo de risco, tendências e diagnósticos prescritivos...")
    df = processar_inteligencia_comercial(df_raw)
    resumo = gerar_resumo_executivo(df)
    logging.info("\n" + resumo)
    df.to_csv("ultimo_resumo_cartao.csv", index=False, encoding="utf-8-sig")

    logging.info("Passo 3/4: A gerar o relatório PDF executivo...")
    data_hoje = datetime.datetime.now().strftime("%Y%m%d")
    nome_pdf = f"Relatorio_Inteligencia_Comercial_{data_hoje}.pdf"
    caminho_pdf = gerar_pdf_relatorio(df, output_pdf=nome_pdf, resumo_texto=resumo)
     
    logging.info("Passo 4/4: A enviar relatórios por e-mail...")
    destinos = _destinatarios ()
    if not destinos:
        logging.warning("Nenhum destinatário configurado. E-mails não serão enviados.")

    else:
                 enviar_email_relatorio(caminho_pdf, destinos, corpo=resumo + "\n\nRelatório completo em anexo.") 

    logging.info("PIPELINE EXECUTADO COM SUCESSO")

if __name__ == "__main__":
    try:
        executar_pipeline()
    except Exception as e:
        logging.error(f"Erro inesperado durante a execução do pipeline: {e}", exc_info=True)
        sys.exit(1)
