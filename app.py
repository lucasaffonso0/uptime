import json
import requests
import yaml
import schedule
import time
from datetime import datetime, timedelta
import ssl
import socket
import mysql.connector
from mysql.connector import pooling

# Desativar verificação de certificado SSL para requests
requests.packages.urllib3.disable_warnings()

# Classe para erro generico
class NotFound(Exception):
    pass

# Carregar configuração de arquivo YAML
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Função para verificar status e expiração do certificado SSL
def check_ssl_expiry(host, timeout):
    context = ssl.create_default_context()
    conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
    conn.settimeout(timeout)  # Definindo timeout de 20 segundos para a conexão
    conn.connect((host, 443))
    cert = conn.getpeercert()

    # Convertendo a data de expiração para um objeto datetime
    expire_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
    days_left = (expire_date - datetime.now()).days

    return expire_date, days_left

# Função para monitorar endpoint HTTP e verificar certificado SSL
def monitor_http(service, db_pool, webhook_url):
    headers = {
    'Content-Type': 'application/json'
    }
    
    msg = None
    
    for host in service['hosts']:
        
        try:
            status, latency, check_time = None, None, datetime.now()
            timeout = int(service['timeout'].replace('s', ''))
            # Verificar status HTTP
            response = requests.get(host, timeout=timeout, verify=False)  # Desativar verificação SSL para requests
            status = response.status_code
            latency = response.elapsed.total_seconds()

            # Verificar status do certificado SSL
            expire_date, days_left = check_ssl_expiry(host.split('//')[1].split('/')[0], timeout)

            expected_status = service['check.response']['status']
            status_match = status in expected_status

            if not status_match:
                raise NotFound("Endpoint não encontrado")

            data = service['tags'][0], service['id'], status, f'{latency:.2f}', check_time.strftime('%Y-%m-%d %H:%M:%S'), status_match, expire_date, days_left
        except requests.Timeout:
            data = service['tags'][0], service['id'], f"Tempo limite excedido 20 segundos", '', check_time.strftime('%Y-%m-%d %H:%M:%S'), '0', datetime.strptime('2000-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'), '0'
            msg = {
            'content': f":sweat:  ({service['tags'][0]}) - {service['hosts']}, Error: Tempo limite excedido 20 segundos, Verificado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'username': 'Uptime'
            }
            requests.post(webhook_url, data=json.dumps(msg), headers=headers)
        except requests.ConnectionError:
            data = service['tags'][0], service['id'], "Não foi possível resolver o nome do host", '', check_time.strftime('%Y-%m-%d %H:%M:%S'), '0', datetime.strptime('2000-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'), '0'
            msg = {
            'content': f":cry: ({service['tags'][0]}) - {service['hosts']}, Error: Não foi possível resolver o nome do host!",
            'username': 'Uptime'
            }
        except NotFound:
            data = service['tags'][0], service['id'], "O endpoint não foi encontrado!", '', check_time.strftime('%Y-%m-%d %H:%M:%S'), '0', datetime.strptime('2000-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'), '0'
            msg = {
            'content': f":grimacing: ({service['tags'][0]}) - {service['hosts']}, Error: O endpoint não foi encontrado!",
            'username': 'Uptime'
            }
        except Exception as e:
            data = service['tags'][0], service['id'], f"Error: {e}", '', check_time.strftime('%Y-%m-%d %H:%M:%S'), '0', datetime.strptime('2000-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'), '0'
            msg = {
            'content': f":cry: ({service['tags'][0]}) - {service['hosts']}, Error: {e}, Verificado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'username': 'Uptime'
            }
        if msg:
            requests.post(webhook_url, data=json.dumps(msg), headers=headers)

        try:
            conn = db_pool.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO uptime (server_name, host, status_code, latency, check_time, status_match, ssl_expiry_date, ssl_days_left)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, data)
            conn.commit()

        except mysql.connector.Error as e:
            msg = {
            'content': f":cry: Erro ao salvar as informações: {e}",
            'username': 'Uptime'
            }
            requests.post(webhook_url, data=json.dumps(msg), headers=headers)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

# Agendar tarefas com base no campo "schedule" apenas para serviços com a tag "ativo"
def schedule_services(config, db_pool, webhook_url):
    for service in config:
        if service['type'] == 'http' and service['enabled']:
            interval = int(service['schedule'].replace('s', ''))
            schedule.every(interval).seconds.do(monitor_http, service=service, db_pool=db_pool, webhook_url=webhook_url)

# Função principal de monitoramento
def main():
    config = load_config('config.yml')

    # Webhook do discord para receber as notificações
    webhook_url = "cole_sua_webhook_aqui"

    # Criar um pool de conexões PostgreSQL
    db_pool = pooling.MySQLConnectionPool(
        pool_name="uptimepool",
        pool_size=5,
        host="",
        port="",
        database="",
        user="",
        password=""
    )

    if db_pool:     
        # Criando a tabela para guardar as informações
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS uptime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_name VARCHAR(128) NOT NULL,
            host VARCHAR(128) NOT NULL,
            status_code VARCHAR(256) NOT NULL,
            latency VARCHAR(128) NOT NULL,
            check_time DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            status_match BOOLEAN NOT NULL,
            ssl_expiry_date DATETIME,
            ssl_days_left INTEGER
        )
        """)
        
        # Confirmar as alterações
        conn.commit()

        # Fechar a conexão
        cursor.close()
        conn.close()
        
        schedule_services(config, db_pool, webhook_url)
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == '__main__':
    main()
