# Pedidos do Restaurante

Sistema para gerenciar os pedidos de um restaurante, feito com Python, MongoDB Atlas e Streamlit.

## Funcionalidades

- **Cadastrar** pedidos com cliente, mesa, itens e observação
- **Consultar** pedidos e ver um resumo com totais
- **Filtrar** por status, cliente, mesa, item e faixa de valor
- **Atualizar** dados, itens e status de um pedido
- **Excluir** pedidos, com confirmação

## Como executar

1. Crie um cluster gratuito (M0) no [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. No Atlas, crie um usuário em **Database Access** e libere o seu IP em **Network Access**.
3. Em **Connect > Drivers**, copie a URL de conexão.
4. Instale o projeto e crie o arquivo de configuração:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

5. Coloque a sua URL no arquivo `.env`, trocando o usuário e a senha.
6. Insira os dados de exemplo (opcional) e abra o sistema:

   ```bash
   python seed.py
   streamlit run app.py
   ```

## Estrutura

| Arquivo | Função |
|---|---|
| `app.py` | Telas do sistema |
| `pedidos.py` | Validações, CRUD e filtros |
| `db.py` | Conexão com o Atlas |
| `seed.py` | Dados de exemplo |
| `test_app.py` | Testes automatizados |

## Modelo de dados

Cada pedido é um documento da coleção `pedidos`, no banco `restaurante`. Os itens ficam dentro do próprio pedido:

```json
{
  "_id": "ObjectId(...)",
  "cliente": "Ana Souza",
  "mesa": 1,
  "itens": [
    { "nome": "Pizza Margherita", "quantidade": 1, "preco_unitario": 45.0 },
    { "nome": "Refrigerante", "quantidade": 2, "preco_unitario": 7.0 }
  ],
  "status": "Recebido",
  "observacao": "Sem cebola",
  "total": 59.0,
  "criado_em": "ISODate(...)"
}
```

## Testes

Os testes usam um banco simulado, então não precisam de conexão com o Atlas:

```bash
pip install -r requirements-dev.txt
pytest
```
