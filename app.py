"""Telas do sistema de pedidos: streamlit run app.py"""
from datetime import timezone
from zoneinfo import ZoneInfo

import streamlit as st
from pymongo.errors import PyMongoError

import db
import pedidos as p

FUSO = ZoneInfo("America/Sao_Paulo")

st.set_page_config(page_title="Pedidos do Restaurante", page_icon="🍽️", layout="wide")


@st.cache_resource(show_spinner="Conectando ao MongoDB Atlas...")
def obter_colecao():
    return db.conectar()


def moeda(valor):
    texto = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def data_local(data):
    if data.tzinfo is None:  # o PyMongo devolve datas em UTC sem fuso
        data = data.replace(tzinfo=timezone.utc)
    return data.astimezone(FUSO).strftime("%d/%m/%Y %H:%M")


def rotulo(pedido):
    return (f"Mesa {pedido['mesa']} · {pedido['cliente']} · {pedido['status']} · "
            f"{moeda(pedido['total'])} · #{str(pedido['_id'])[-6:]}")


def concluir(mensagem):
    """Guarda a mensagem de sucesso e recarrega a tela."""
    st.session_state["mensagem"] = mensagem
    st.rerun()


def seletor_itens(prefixo, itens_atuais=()):
    """Mostra um campo de quantidade por prato e devolve os itens escolhidos."""
    atuais = {item["nome"]: item for item in itens_atuais}
    # Pedidos antigos mantêm o preço e os pratos com que foram feitos
    precos = {**p.CARDAPIO, **{n: i["preco_unitario"] for n, i in atuais.items()}}

    itens = []
    colunas = st.columns(2)
    for indice, (nome, preco) in enumerate(precos.items()):
        quantidade = colunas[indice % 2].number_input(
            f"{nome} ({moeda(preco)})",
            min_value=0,
            step=1,
            value=atuais[nome]["quantidade"] if nome in atuais else 0,
            key=f"{prefixo}_{nome}",
        )
        if quantidade > 0:
            itens.append({"nome": nome, "quantidade": quantidade, "preco_unitario": preco})
    return itens


def tela_consultar(colecao):
    st.header("Consultar pedidos")

    resumo = p.resumo_por_status(colecao)
    faturado = sum(g["valor"] for s, g in resumo.items() if s != "Cancelado")
    em_andamento = sum(resumo[s]["quantidade"] for s in ("Recebido", "Em preparo", "Pronto")
                       if s in resumo)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de pedidos", sum(g["quantidade"] for g in resumo.values()))
    c2.metric("Em andamento", em_andamento)
    c3.metric("Valor sem cancelados", moeda(faturado))

    st.subheader("Filtros")
    c1, c2, c3 = st.columns(3)
    status = c1.multiselect("Status", p.STATUS)
    cliente = c2.text_input("Nome do cliente contém")
    item = c3.selectbox("Contém o item", list(p.CARDAPIO), index=None, placeholder="Qualquer item")
    c1, c2, c3 = st.columns(3)
    mesa = c1.number_input("Mesa", min_value=1, step=1, value=None, placeholder="Qualquer mesa")
    total_min = c2.number_input("Total mínimo (R$)", min_value=0.0, value=None, placeholder="Sem mínimo")
    total_max = c3.number_input("Total máximo (R$)", min_value=0.0, value=None, placeholder="Sem máximo")

    filtro = p.montar_filtro(status, mesa, cliente.strip(), item, total_min, total_max)
    with st.expander("Ver a consulta enviada ao MongoDB"):
        st.code(f"db.pedidos.find({filtro})", language="javascript")

    resultado = p.listar_pedidos(colecao, filtro)
    st.subheader(f"{len(resultado)} pedido(s) encontrado(s)")
    if not resultado:
        st.info("Nenhum pedido atende a esses filtros.")
        return

    st.dataframe(
        [
            {
                "Código": str(pedido["_id"])[-6:],
                "Data": data_local(pedido["criado_em"]),
                "Mesa": pedido["mesa"],
                "Cliente": pedido["cliente"],
                "Itens": ", ".join(f"{i['quantidade']}x {i['nome']}" for i in pedido["itens"]),
                "Total": moeda(pedido["total"]),
                "Status": pedido["status"],
                "Observação": pedido["observacao"],
            }
            for pedido in resultado
        ],
        width="stretch",
        hide_index=True,
    )


def tela_novo(colecao):
    st.header("Novo pedido")
    with st.form("novo_pedido", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        cliente = c1.text_input("Cliente")
        mesa = c2.number_input("Mesa", min_value=1, step=1)
        st.write("**Itens**")
        itens = seletor_itens("novo")
        observacao = st.text_input("Observação")
        enviado = st.form_submit_button("Cadastrar pedido", type="primary")

    if enviado:
        try:
            p.criar_pedido(colecao, cliente, mesa, itens, observacao=observacao)
        except ValueError as erro:
            st.error(str(erro))
        else:
            concluir(f"Pedido de {cliente.strip()} cadastrado.")


def escolher_pedido(colecao):
    """Mostra a lista de pedidos para seleção. Devolve None se não houver nenhum."""
    lista = p.listar_pedidos(colecao)
    if not lista:
        st.info("Ainda não há pedidos cadastrados.")
        return None
    return st.selectbox("Pedido", lista, format_func=rotulo)


def tela_atualizar(colecao):
    st.header("Atualizar pedido")
    pedido = escolher_pedido(colecao)
    if pedido is None:
        return

    prefixo = f"editar_{pedido['_id']}"
    with st.form(prefixo):
        c1, c2, c3 = st.columns([3, 1, 2])
        cliente = c1.text_input("Cliente", value=pedido["cliente"], key=f"{prefixo}_cliente")
        mesa = c2.number_input("Mesa", min_value=1, step=1, value=pedido["mesa"], key=f"{prefixo}_mesa")
        status = c3.selectbox("Status", p.STATUS, index=p.STATUS.index(pedido["status"]),
                              key=f"{prefixo}_status")
        st.write("**Itens**")
        itens = seletor_itens(prefixo, pedido["itens"])
        observacao = st.text_input("Observação", value=pedido["observacao"], key=f"{prefixo}_obs")
        enviado = st.form_submit_button("Salvar alterações", type="primary")

    if enviado:
        try:
            encontrado = p.atualizar_pedido(colecao, pedido["_id"], cliente, mesa, itens, status, observacao)
        except ValueError as erro:
            st.error(str(erro))
        else:
            if encontrado:
                concluir("Pedido atualizado.")
            st.error("Esse pedido não existe mais.")


def tela_excluir(colecao):
    st.header("Excluir pedido")
    pedido = escolher_pedido(colecao)
    if pedido is None:
        return

    st.write("**Itens:** " + ", ".join(f"{i['quantidade']}x {i['nome']}" for i in pedido["itens"]))
    confirmado = st.checkbox("Confirmo que quero excluir este pedido", key=f"confirmar_{pedido['_id']}")
    if st.button("Excluir pedido", type="primary", disabled=not confirmado):
        if p.excluir_pedido(colecao, pedido["_id"]):
            concluir("Pedido excluído.")
        st.error("Esse pedido não existe mais.")


TELAS = {
    "🔍 Consultar": tela_consultar,
    "➕ Novo pedido": tela_novo,
    "✏️ Atualizar": tela_atualizar,
    "🗑️ Excluir": tela_excluir,
}

st.sidebar.title("🍽️ Restaurante")
tela = st.sidebar.radio("Menu", list(TELAS), label_visibility="collapsed")

if "mensagem" in st.session_state:
    st.success(st.session_state.pop("mensagem"))

try:
    TELAS[tela](obter_colecao())
except RuntimeError as erro:
    st.error(str(erro))
except PyMongoError as erro:
    st.error("Não foi possível acessar o MongoDB. Verifique a URL no arquivo .env, "
             "o usuário do banco e a liberação do seu IP no Atlas.")
    with st.expander("Detalhes do erro"):
        st.code(str(erro))
