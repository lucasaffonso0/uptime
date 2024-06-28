---

# Monitor de Uptime

Este projeto é um script em python baseado no Heartbeat do Elasticsearch, para monitorar o uptime de uma ou varias aplicações. Ele utiliza um arquivo de configuração `config.yml` para especificar os sites que devem ser monitorados. 

## Pré-requisitos

Antes de executar o script, você precisará instalar as dependências necessárias. As dependências estão listadas no arquivo `requirements.txt`.

## Instalação

1. Clone o repositório para a sua máquina local:

    ```bash
    git clone https://github.com/lucasaffonso0/uptime.git
    cd uptime
    ```

2. Crie um ambiente virtual (opcional, mas recomendado):

    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows use: venv\Scripts\activate
    ```

3. Instale as dependências:

    ```bash
    pip install -r requirements.txt
    ```

## Configuração

### Arquivo config.yml
O script utiliza um arquivo `config.yml` para especificar os sites a serem monitorados. A estrutura do arquivo é a seguinte:

```yaml
- type: http
  tags:
    - servidor01
  id: meudominio.com.br
  enabled: true
  schedule: '30s'
  hosts:
    - 'https://meudominio.com.br/health'
  timeout: 30s
  check.response:
    status:
      - 200
```

Você pode adicionar quantos sites quiser, seguindo o mesmo formato.

### Banco de Dados MySQL

O script também requer a configuração de um banco de dados MySQL. A configuração é feita através de um pool de conexões:

```python
db_pool = pooling.MySQLConnectionPool(
    pool_name="uptimepool",
    pool_size=5,
    host="",
    port="",
    database="",
    user="",
    password=""
)
```
Preencha os valores de host, port, database, user e password com as informações do seu banco de dados MySQL.

### Notificações para o Discord

Para o script enviar notificações para o discord, substitua o "cole_sua_webhook_aqui" pela sua webhook do discord

```python
  webhook_url = "cole_sua_webhook_aqui"
```

## Uso

Para executar o script de monitoramento de uptime, use o comando:

```bash
python app.py
```

O script irá lê o arquivo `config.yml`, monitorar os sites listados e salvará as metricas no banco de dados configurado na aplicação

## Contribuição

Contribuições são bem-vindas! Se você encontrar algum problema ou tiver sugestões de melhorias, sinta-se à vontade para abrir uma issue ou enviar um pull request.
