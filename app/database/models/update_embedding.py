import logging
import json
from app.database.connexao import get_connection_mysql

def update_embedding(embedding, id_colaborador):
    try:
        conn = get_connection_mysql()
        cursor = conn.cursor()
        cursor.execute("UPDATE colaborador SET embedding = %s WHERE id = %s",(json.dumps(embedding), id_colaborador))
        conn.commit()
        cursor.close()
        conn.close()
        logging.info(f"Embedding atualizado com sucesso!")
        return True
    except Exception as e:
        logging.error(f"Erro ao atualizar embedding: {e}")
        return False