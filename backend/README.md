# MedFlux — Backend (Flask)

Autenticação da API consumida pelo frontend em `http://localhost:5000/api`.

## Como rodar

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Linux/Mac: cp .env.example .env  -> troque o JWT_SECRET
python seed.py                  # cria marina.santos@medflux.com / 123456
python app.py                   # sobe em http://localhost:5000
```

Testes: `python -m unittest -v test_auth`

## Endpoints

| Método | Rota | Auth | Resposta |
|---|---|---|---|
| POST | `/api/auth/login` | — | `200 { token, user: { name, city, avatarInitials } }` · `400` · `401` |
| POST | `/api/auth/register` | — | `201` mesmo formato do login · `400` · `409` |
| GET | `/api/auth/me` | Bearer | `200 { name, city, avatarInitials }` · `401` |

Erros sempre em JSON: `{ "message": "..." }`. Exemplos em `requests.http`.

## Banco de dados

Usa SQLAlchemy, então trocar de banco é só mudar `DATABASE_URL`:

- Local (padrão): `sqlite:///medflux.db`
- Supabase (Postgres): `pip install "psycopg[binary]"` e use a connection string do painel
  (Project Settings → Database), trocando o prefixo para `postgresql+psycopg://`.

A tabela `users` é criada automaticamente na inicialização. O Qdrant não participa da autenticação.

## Limitações conhecidas do frontend (não corrigidas aqui)

- `requestJson` em `src/services/api.ts` captura qualquer erro (inclusive 401) e devolve um login mock,
  então uma senha errada ainda "loga" no frontend atual. O backend responde 401 corretamente.
- O frontend não envia `Authorization` nas rotas de triagem/unidades, por isso só `/api/auth/me`
  é protegida. Para proteger outras rotas, use o decorator `require_auth` de `auth.py`.
