import sys
import logging
import datetime
import pandas as pd
from etl import carregar_dados_comerciais
from analytics import processar_inteligencia_comercial
from generator import gerar_pdf_relatorio
from notifier import enviar_email_relatorio

# Configuração de Logging para auditoria e acompanhamento
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("execucao_pipeline.log", encoding="utf-8")
    ]
)

def executar_pipeline():
    logging.info("==================================================")
    logging.info("INICIANDO MOTOR DE INTELIGÊNCIA COMERCIAL")
    logging.info("==================================================")
    
    try:
       
        logging.info("Passo 1/4: A extrair dados do SQL Server via ETL...")
        df_raw = carregar_dados_comerciais()
        
        if df_raw.empty:
            logging.warning("Nenhum registo retornado do banco de dados. Pipeline interrompido.")
            return
        
        logging.info(f"ETL concluído com sucesso. Registos mensais carregados: {len(df_raw)}")

        logging.info("Passo 2/4: A processar o algoritmo de risco, tendências e diagnósticos prescritivos...")
        df_resumo = processar_inteligencia_comercial(df_raw)
        
        total_clientes = len(df_resumo)
        criticos = len(df_resumo[df_resumo['status'] == 'Crítico'])
        atencao = len(df_resumo[df_resumo['status'] == 'Atenção'])
        
        logging.info(f"Análise concluída. {total_clientes} clientes processados ({criticos} Críticos 🔴, {atencao} Atenção 🟠).")

        ficheiro_csv = "ultimo_resumo_carteira.csv"
        df_resumo.to_csv(ficheiro_csv, index=False, encoding="utf-8-sig")
        logging.info(f"Backup de auditoria guardado em: {ficheiro_csv}")

        logging.info("Passo 3/4: A gerar o relatório PDF executivo...")
        data_hoje = datetime.datetime.now().strftime('%Y%m%d')
        nome_pdf = f"Relatorio_Inteligencia_Comercial_{data_hoje}.pdf"
        caminho_pdf = gerar_pdf_relatorio(df_resumo, output_pdf=nome_pdf)
        logging.info(f"Ficheiro PDF gerado com sucesso: {caminho_pdf}")

        logging.info("Passo 4/4: A enviar relatórios por e-mail...")
        destinatarios = [
            "diretoria@transportadora.com.br",
            "gerencia.comercial@transportadora.com.br"
        ]
        enviar_email_relatorio(caminho_pdf, destinatarios)
        logging.info("E-mails disparados com sucesso!")

        logging.info("==================================================")
        logging.info("PIPELINE EXECUTADO COM SUCESSO")
        logging.info("==================================================")

    except Exception as e:
        logging.error(f"FALHA CRÍTICA NA EXECUÇÃO DO PIPELINE: {str(e)}", exc_info=True)

if __name__ == "__main__":
    executar_pipeline()