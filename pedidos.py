"""Regras do negócio e operações de CRUD dos pedidos."""
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

STATUS = ["Recebido", "Em preparo", "Pronto", "Entregue", "Cancelado"]

CARDAPIO = {
    "Pizza Margherita": 45.00,
    "Hambúrguer Artesanal": 32.50,
    "Lasanha à Bolonhesa": 38.00,
    "Salada Caesar": 24.00,
    "Batata Frita": 18.00,
    "Refrigerante": 7.00,
    "Suco Natural": 10.00,
    "Pudim": 12.00,
}


def _montar_dados(cliente, mesa, itens, status, observacao):
    """Valida os campos e devolve o documento pronto para salvar."""
    cliente = cliente.strip()
    if not cliente:
        raise ValueError("Informe o nome do cliente.")
    if mesa < 1:
        raise ValueError("A mesa deve ser maior que zero.")
    if not itens:
        raise ValueError("Adicione pelo menos um item ao pedido.")
    if status not in STATUS:
        raise ValueError(f"Status inválido: {status}")
    if any(item["quantidade"] < 1 or item["preco_unitario"] < 0 for item in itens):
        raise ValueError("Quantidade ou preço de item inválido.")

    total = sum(item["quantidade"] * item["preco_unitario"] for item in itens)
    return {
        "cliente": cliente,
        "mesa": mesa,
        "itens": itens,
        "status": status,
        "observacao": observacao.strip(),
        "total": round(total, 2),
    }


def _para_object_id(pedido_id):
    try:
        return ObjectId(pedido_id)
    except (InvalidId, TypeError) as erro:
        raise ValueError(f"ID de pedido inválido: {pedido_id}") from erro


# CREATE
def criar_pedido(colecao, cliente, mesa, itens, status="Recebido", observacao=""):
    pedido = _montar_dados(cliente, mesa, itens, status, observacao)
    pedido["criado_em"] = datetime.now(timezone.utc)
    return colecao.insert_one(pedido).inserted_id


# READ
def montar_filtro(status=None, mesa=None, cliente=None, item=None,
                  total_min=None, total_max=None):
    """Transforma os filtros preenchidos em uma consulta do MongoDB."""
    filtro = {}
    if status:
        filtro["status"] = {"$in": status}
    if mesa is not None:
        filtro["mesa"] = mesa
    if cliente:
        # re.escape impede que o texto digitado seja interpretado como regex
        filtro["cliente"] = {"$regex": re.escape(cliente), "$options": "i"}
    if item:
        # A notação de ponto consulta um campo dentro da lista de itens
        filtro["itens.nome"] = item
    if total_min is not None or total_max is not None:
        filtro["total"] = {}
        if total_min is not None:
            filtro["total"]["$gte"] = total_min
        if total_max is not None:
            filtro["total"]["$lte"] = total_max
    return filtro


def listar_pedidos(colecao, filtro=None):
    """Devolve os pedidos que atendem ao filtro, do mais novo ao mais antigo."""
    return list(colecao.find(filtro or {}).sort("criado_em", -1))


def buscar_pedido(colecao, pedido_id):
    return colecao.find_one({"_id": _para_object_id(pedido_id)})


def resumo_por_status(colecao):
    """Usa uma agregação para contar pedidos e somar valores por status."""
    pipeline = [
        {"$group": {"_id": "$status", "quantidade": {"$sum": 1}, "valor": {"$sum": "$total"}}}
    ]
    return {grupo["_id"]: grupo for grupo in colecao.aggregate(pipeline)}


# UPDATE
def atualizar_pedido(colecao, pedido_id, cliente, mesa, itens, status, observacao=""):
    """Atualiza o pedido. Devolve False se ele não existir mais."""
    dados = _montar_dados(cliente, mesa, itens, status, observacao)
    dados["atualizado_em"] = datetime.now(timezone.utc)
    resultado = colecao.update_one({"_id": _para_object_id(pedido_id)}, {"$set": dados})
    return resultado.matched_count == 1


# DELETE
def excluir_pedido(colecao, pedido_id):
    """Exclui o pedido. Devolve False se ele não existir mais."""
    resultado = colecao.delete_one({"_id": _para_object_id(pedido_id)})
    return resultado.deleted_count == 1
