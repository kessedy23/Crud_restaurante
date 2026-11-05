"""Insere pedidos de exemplo se a coleção estiver vazia: python seed.py"""
from db import conectar
from pedidos import CARDAPIO, criar_pedido

EXEMPLOS = [
    ("Ana Souza", 1, {"Pizza Margherita": 1, "Refrigerante": 2}, "Recebido", "Sem cebola"),
    ("Bruno Lima", 3, {"Hambúrguer Artesanal": 2, "Batata Frita": 1}, "Em preparo", ""),
    ("Carla Dias", 2, {"Salada Caesar": 1, "Suco Natural": 1}, "Pronto", ""),
    ("Diego Alves", 5, {"Lasanha à Bolonhesa": 2, "Pudim": 2}, "Entregue", "Aniversário"),
    ("Elisa Rocha", 4, {"Pizza Margherita": 2, "Suco Natural": 3}, "Entregue", ""),
    ("Fábio Melo", 1, {"Batata Frita": 1}, "Cancelado", "Cliente desistiu"),
]


def main():
    colecao = conectar()
    if colecao.count_documents({}) > 0:
        print("A coleção já tem pedidos. Nada foi inserido.")
        return

    for cliente, mesa, quantidades, status, observacao in EXEMPLOS:
        itens = [
            {"nome": nome, "quantidade": quantidade, "preco_unitario": CARDAPIO[nome]}
            for nome, quantidade in quantidades.items()
        ]
        criar_pedido(colecao, cliente, mesa, itens, status, observacao)
    print(f"{len(EXEMPLOS)} pedidos inseridos.")


if __name__ == "__main__":
    main()
