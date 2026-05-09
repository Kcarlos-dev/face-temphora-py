import logging

import mysql.connector

from app.config.env_config import get_env_config


def _ssl_kwargs(cfg: dict) -> dict:
    """SSL no padrão Node (mysql2): liga/desliga + valida ou não.

    - cfg['mysql_ssl'] = False → conexão em texto puro.
    - cfg['mysql_ssl'] = True  → força SSL.
        - reject_unauthorized=True  → valida cert do servidor (recomendado).
        - reject_unauthorized=False → criptografa, mas aceita qualquer cert.

    Sem `ssl_ca`, o driver usa o trust store do sistema (já cobre Cloud SQL/GCP,
    AWS RDS, etc., porque seus certs são assinados por CAs públicas).
    """
    if not cfg["mysql_ssl"]:
        return {}

    verify = cfg["mysql_ssl_reject_unauthorized"]
    return {
        "ssl_disabled": False,
        "ssl_verify_cert": verify,
        "ssl_verify_identity": verify,
    }


def get_connection_mysql():
    cfg = get_env_config()
    try:
        conn = mysql.connector.connect(
            pool_name="mysql_face_temphora",
            pool_size=10,
            host=cfg["mysql_host"],
            user=cfg["mysql_user"],
            password=cfg["mysql_password"],
            database=cfg["mysql_database"],
            port=cfg["mysql_port"],
            **_ssl_kwargs(cfg),
        )
        return conn
    except Exception as e:
        logging.error(f"Erro ao conectar ao banco MySQL: {e}")
        return None
