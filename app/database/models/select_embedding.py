import logging
import json
from app.database.connexao import get_connection_mysql

def select_embedding(id_empresa):
    try:
        conn = get_connection_mysql()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, embedding FROM colaborador WHERE id_empresa = %s",(id_empresa,))
        embedding = cursor.fetchall()
        cursor.close()
        conn.close()
        return embedding
    except Exception as e:
        logging.error(f"Erro ao selecionar embedding: {e}")
        return False