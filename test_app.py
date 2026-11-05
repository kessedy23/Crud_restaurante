from unittest.mock import patch

import mongomock
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import pedidos as p


@pytest.fixture
def colecao():
    return mongomock.MongoClient()["restaurante"]["pedidos"]


def item(nome="Pudim", quantidade=1, preco=12.0):
    return {"nome": nome, "quantidade": quantidade, "preco_unitario": preco}


def nomes(lista):
    return sorted(pedido["cliente"] for pedido in lista)


def test_criar_calcula_total(colecao):
    pedido_id = p.criar_pedido(colecao, " Ana ", 1, [item(quantidade=2), item("Suco", 1, 10.0)])
    pedido = p.buscar_pedido(colecao, pedido_id)
    assert pedido["cliente"] == "Ana"
    assert pedido["total"] == 34.0
    assert pedido["status"] == "Recebido"


@pytest.mark.parametrize("cliente, mesa, itens", [
    ("  ", 1, [item()]),
    ("Ana", 0, [item()]),
    ("Ana", 1, []),
    ("Ana", 1, [item(quantidade=0)]),
])
def test_criar_rejeita_dados_invalidos(colecao, cliente, mesa, itens):
    with pytest.raises(ValueError):
        p.criar_pedido(colecao, cliente, mesa, itens)
    assert colecao.count_documents({}) == 0


def test_filtros(colecao):
    p.criar_pedido(colecao, "Ana Souza", 1, [item("Pudim", 1, 10.0)], "Recebido")
    p.criar_pedido(colecao, "Bruno", 2, [item("Suco", 3, 10.0)], "Pronto")
    p.criar_pedido(colecao, "Mariana", 1, [item("Suco", 5, 10.0)], "Entregue")

    def buscar(**filtros):
        return nomes(p.listar_pedidos(colecao, p.montar_filtro(**filtros)))

    assert buscar() == ["Ana Souza", "Bruno", "Mariana"]
    assert buscar(status=["Pronto", "Entregue"]) == ["Bruno", "Mariana"]
    assert buscar(mesa=1) == ["Ana Souza", "Mariana"]
    assert buscar(cliente="ANA") == ["Ana Souza", "Mariana"]
    assert buscar(item="Suco") == ["Bruno", "Mariana"]
    assert buscar(total_min=30.0, total_max=30.0) == ["Bruno"]
    assert buscar(total_min=0.0, total_max=10.0) == ["Ana Souza"]
    assert buscar(mesa=1, item="Suco") == ["Mariana"]


def test_filtro_de_cliente_nao_interpreta_regex(colecao):
    p.criar_pedido(colecao, "Ana", 1, [item()])
    assert p.listar_pedidos(colecao, p.montar_filtro(cliente=".*")) == []


def test_atualizar(colecao):
    pedido_id = p.criar_pedido(colecao, "Ana", 1, [item()])
    assert p.atualizar_pedido(colecao, pedido_id, "Ana", 2, [item(quantidade=3)], "Pronto")
    pedido = p.buscar_pedido(colecao, pedido_id)
    assert (pedido["mesa"], pedido["status"], pedido["total"]) == (2, "Pronto", 36.0)
    assert "criado_em" in pedido and "atualizado_em" in pedido


def test_excluir(colecao):
    pedido_id = p.criar_pedido(colecao, "Ana", 1, [item()])
    assert p.excluir_pedido(colecao, pedido_id)
    assert not p.excluir_pedido(colecao, pedido_id)
    assert not p.atualizar_pedido(colecao, pedido_id, "Ana", 1, [item()], "Pronto")


def test_id_invalido(colecao):
    with pytest.raises(ValueError):
        p.buscar_pedido(colecao, "abc")


def test_resumo(colecao):
    p.criar_pedido(colecao, "Ana", 1, [item(preco=10.0)], "Pronto")
    p.criar_pedido(colecao, "Bia", 1, [item(preco=20.0)], "Pronto")
    resumo = p.resumo_por_status(colecao)
    assert resumo["Pronto"]["quantidade"] == 2
    assert resumo["Pronto"]["valor"] == 30.0


# Testes das telas: executam app.py de verdade, com um banco simulado


@pytest.fixture
def tela(colecao):
    st.cache_resource.clear()
    with patch("db.conectar", return_value=colecao):
        yield AppTest.from_file("app.py", default_timeout=20)
    st.cache_resource.clear()


def ir_para(app, nome):
    menu = app.sidebar.radio[0]
    opcao = next(o for o in menu.options if nome in o)
    menu.set_value(opcao).run()
    assert not app.exception


def test_tela_cadastro_ate_exclusao(tela, colecao):
    tela.run()
    assert not tela.exception

    # Cadastrar
    ir_para(tela, "Novo pedido")
    tela.text_input[0].set_value("Carla")
    tela.number_input[0].set_value(4)
    next(n for n in tela.number_input if "Pudim" in n.label).set_value(2)
    tela.button[0].click().run()
    assert not tela.exception
    pedido = colecao.find_one({"cliente": "Carla"})
    assert pedido["mesa"] == 4 and pedido["total"] == 24.0
    assert "cadastrado" in tela.success[0].value

    # Consultar com filtro
    ir_para(tela, "Consultar")
    assert "1 pedido" in tela.subheader[1].value
    tela.text_input[0].set_value("nao existe").run()
    assert "0 pedido" in tela.subheader[1].value

    # Atualizar
    ir_para(tela, "Atualizar")
    tela.selectbox[1].set_value("Pronto")
    next(n for n in tela.number_input if "Pudim" in n.label).set_value(3)
    tela.button[0].click().run()
    assert not tela.exception
    pedido = colecao.find_one({"cliente": "Carla"})
    assert pedido["status"] == "Pronto" and pedido["total"] == 36.0

    # Excluir só depois de confirmar
    ir_para(tela, "Excluir")
    assert tela.button[0].disabled
    tela.checkbox[0].check().run()
    tela.button[0].click().run()
    assert not tela.exception
    assert colecao.count_documents({}) == 0


def test_tela_recusa_pedido_sem_itens(tela, colecao):
    tela.run()
    ir_para(tela, "Novo pedido")
    tela.text_input[0].set_value("Carla")
    tela.button[0].click().run()
    assert "pelo menos um item" in tela.error[0].value
    assert colecao.count_documents({}) == 0


def test_tela_avisa_sem_configuracao():
    st.cache_resource.clear()
    with patch("db.load_dotenv"), patch.dict("os.environ", clear=True):
        app = AppTest.from_file("app.py", default_timeout=20).run()
    assert not app.exception
    assert "MONGODB_URI" in app.error[0].value
