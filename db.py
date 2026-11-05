"""Conexão com o MongoDB Atlas."""
import os

from dotenv import load_dotenv
from pymongo import MongoClient

NOME_BANCO = "restaurante"
NOME_COLECAO = "pedidos"


def conectar():
    """Conecta ao Atlas e devolve a coleção de pedidos."""
    load_dotenv()
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI não configurada. Copie .env.example para .env e "
            "preencha com a URL do seu cluster."
        )

    cliente = MongoClient(uri, serverSelectionTimeoutMS=5000)
    cliente.admin.command("ping")  # falha aqui se a conexão não funcionar
    return cliente[NOME_BANCO][NOME_COLECAO]
