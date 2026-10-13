# MedFlux — Backend

API do **MedFlux - Health & Wellness**: cadastro e autenticação, perfil com foto, triagem inteligente
com IA (OpenRouter + agentes AG2), histórico de sintomas e consultas, banco vetorial para contexto
clínico e mapa de unidades de saúde (UPA/UBS) de Marília/SP.

## Sumário

- [Objetivo](#objetivo)
- [Stack](#stack)
- [Arquitetura](#arquitetura)
- [Como rodar com Docker Compose](#como-rodar-com-docker-compose)
- [Como rodar localmente (sem Docker para a API)](#como-rodar-localmente-sem-docker-para-a-api)
- [Configuração do .env](#configuração-do-env)
- [Migrations (Alembic)](#migrations-alembic)
- [Testar autenticação no Swagger](#testar-autenticação-no-swagger)
- [Endpoints](#endpoints)
- [Exemplos de payload](#exemplos-de-payload)
- [Triagem, agentes e OpenRouter](#triagem-agentes-e-openrouter)
- [Banco vetorial (Qdrant)](#banco-vetorial-qdrant)
- [Arquivos no MinIO](#arquivos-no-minio)
- [Integração com o frontend](#integração-com-o-frontend)
- [Testes](#testes)
- [Segurança](#segurança)
- [Decisões técnicas](#decisões-técnicas)

## Objetivo

Servir o frontend React do MedFlux no fluxo **login → dashboard → chat de triagem → mapa → perfil/foto**,
com uma base pronta para evoluir para IA real: a triagem já funciona com LLM via OpenRouter e, sem
chave configurada, responde com regras determinísticas no mesmo formato.

> A triagem é uma **orientação inicial** sobre qual serviço procurar (UPA ou UBS). Não é diagnóstico.

## Stack

| Camada | Tecnologia |
|---|---|
| API | Python 3.11+ (imagem 3.12), FastAPI, Uvicorn, Pydantic v2 |
| Banco relacional | MySQL 8.4, SQLAlchemy 2.x (async, `aiomysql`), Alembic |
| Banco vetorial | Qdrant |
| Arquivos | MinIO (API S3) |
| Cache / rate limit | Redis (opcional) |
| IA | OpenRouter (API compatível com OpenAI) via `httpx` assíncrono |
| Agentes | AG2 (sucessor do AutoGen) ou runtime próprio, trocável por variável de ambiente |
| Auth | JWT (PyJWT) + bcrypt |
| Testes | pytest + anyio, SQLite e Qdrant em memória, MinIO/OpenRouter mockados |

## Arquitetura

```
Frontend React ──HTTP/JSON + JWT──▶ FastAPI (app/api/v1/routes)
                                         │  Depends(...) injeta serviços
                                         ▼
                                   services/  (regras de negócio)
                     ┌───────────────┼──────────────────┬───────────────┐
                     ▼               ▼                  ▼               ▼
              repositories/     agents/ ──runtime──▶ OpenRouter     integrations/
              (MySQL, Qdrant,   symptoms → triage →  (custom | AG2)  (clientes MinIO,
               MinIO)           summarizer                           Qdrant, OpenRouter)
```

```
app/
├── api/v1/routes/      auth, users, triage, health_units, files, agents, vector
├── api/v1/deps.py      sessão do banco, usuário autenticado, fábrica de serviços
├── core/               config, security (JWT/bcrypt), logging JSON, constants, exceptions, middleware
├── db/models/          User, TriageSession, TriageMessage, HealthUnit, SymptomRecord, AgentEvent, DiseaseEmbedding
├── db/repositories/    acesso a dados (MySQL, Qdrant, MinIO)
├── schemas/            contratos Pydantic de entrada e saída
├── services/           auth, user, triage, storage, vector, ai, agent, prompt
├── integrations/       clientes OpenRouter, Qdrant e MinIO
├── agents/             base_agent, runtime (custom/AG2), triage, symptoms, summarizer
├── prompts/            prompts de triagem, assistente e consulta de doenças
├── utils/              embeddings locais, hash, validação de arquivos e campos
├── main.py             create_app() + lifespan (cria/fecha conexões)
└── seed.py             usuário demo, admin e base de doenças
alembic/                migrations (schema + seed das unidades de saúde)
docker/                 init do MySQL, buckets do MinIO e config do Qdrant
tests/                  suíte pytest
```

Relacionamentos: `User 1:N TriageSession`, `TriageSession 1:N TriageMessage`, `User 1:N SymptomRecord`,
`User 1:N AgentEvent`. Exclusão de usuário remove os dados dele em cascata.

## Como rodar com Docker Compose

Pré-requisito: Docker Desktop (ou Docker Engine + Compose v2).

```bash
cd backend
cp .env.example .env          # Windows: copy .env.example .env
# edite o .env: troque todas as senhas/segredos "troque-..."
docker compose up -d --build
```

O compose sobe, nesta ordem e com healthchecks:

| Serviço | Porta no host | Função |
|---|---|---|
| `mysql` | `3306` (`MYSQL_HOST_PORT`) | banco relacional; `docker/mysql/init/01-init.sql` roda na 1ª criação |
| `minio` | `9000` (API), `9001` (console) | arquivos |
| `minio-init` | — | cria os buckets (`docker/minio/init/init-buckets.sh`) e encerra |
| `qdrant` | `6333` (HTTP), `6334` (gRPC) | banco vetorial (`docker/qdrant/config/qdrant.yaml`) |
| `redis` | `6379` | rate limit de login |
| `backend` | `5000` | roda `alembic upgrade head`, `python -m app.seed` e a API |

Verificação:

```bash
curl http://localhost:5000/healthz   # {"status":"ok"}
curl http://localhost:5000/readyz    # estado de MySQL, Qdrant, MinIO, Redis e OpenRouter
```

- Documentação interativa: http://localhost:5000/docs (Swagger) e http://localhost:5000/redoc
- Console do MinIO: http://localhost:9001 (usuário/senha = `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`)
- Dashboard do Qdrant: http://localhost:6333/dashboard

Usuário demo criado pelo seed: **marina.santos@medflux.com / 123456**. Administrador: `SEED_ADMIN_EMAIL` /
`SEED_ADMIN_PASSWORD` do `.env`.

Comandos úteis:

```bash
docker compose logs -f backend      # logs JSON da API
docker compose down                 # para tudo (mantém os dados)
docker compose down -v              # para e APAGA volumes (mysql_data, minio_data, qdrant_data)
```

> Já existe um MySQL na porta 3306 da sua máquina? Defina `MYSQL_HOST_PORT=3307` e `DB_PORT=3307` no `.env`.

> **Imagem do MinIO:** a MinIO Inc. deixou de publicar `minio/minio` no Docker Hub em 2025. O compose usa
> `pgsty/minio` / `pgsty/mc`, fork comunitário com o mesmo binário e CLI. Para usar outra imagem, defina
> `MINIO_IMAGE` e `MINIO_MC_IMAGE` no `.env`.

## Como rodar localmente (sem Docker para a API)

Útil para desenvolver com reload. A infraestrutura continua no Docker:

```bash
cd backend
docker compose up -d mysql minio minio-init qdrant redis

python -m venv .venv
.venv\Scripts\activate              # Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt

alembic upgrade head
python -m app.seed
uvicorn app.main:create_app --factory --reload --port 5000
```

No `.env`, os hosts ficam como `localhost` (o compose sobrescreve para os nomes dos serviços dentro do Docker).

## Configuração do .env

O `.env` **não é versionado** (`.gitignore`). O `.env.example` documenta todas as variáveis:

| Grupo | Variáveis | Observações |
|---|---|---|
| App | `APP_ENV`, `APP_PORT`, `LOG_LEVEL`, `FRONTEND_URL` | `FRONTEND_URL` aceita várias origens separadas por vírgula (CORS) |
| MySQL (container) | `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST_PORT` | usadas pela imagem do MySQL |
| MySQL (API) | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | mesmos valores do bloco acima. `DATABASE_URL` sobrescreve tudo, se definido |
| MinIO | `MINIO_ENDPOINT`, `MINIO_PUBLIC_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE`, `PRESIGNED_URL_EXPIRE_MINUTES` | `MINIO_PUBLIC_ENDPOINT` é o host que o navegador acessa |
| Qdrant | `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`, `EMBEDDING_DIM` | |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_SECONDS` | sem `REDIS_HOST` o rate limit fica desligado |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `OPENROUTER_TIMEOUT` | chave vazia = fallback determinístico |
| Agentes | `AGENT_RUNTIME` | `custom` ou `ag2` |
| JWT | `JWT_SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | segredo com no mínimo 32 caracteres (a API não sobe sem ele) |
| Seed | `SEED_DEMO_USER`, `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD` | usuário demo é ignorado em `APP_ENV=production` |

Gerar segredos: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Migrations (Alembic)

A URL do banco vem do `.env` (via `app.core.config`), então o `alembic.ini` não tem credenciais.

```bash
alembic upgrade head                                  # aplica as migrations
alembic downgrade -1                                  # desfaz a última
alembic revision --autogenerate -m "descricao"        # gera migration a partir dos models
alembic check                                         # confere se models e banco estão em sincronia
alembic upgrade head --sql                            # mostra o SQL sem executar
```

A migration inicial (`0001`) cria as 7 tabelas e insere as 4 unidades de saúde exibidas no mapa.
No Docker, `alembic upgrade head` roda automaticamente ao iniciar o backend.

## Testar autenticação no Swagger

Com a API no ar, abra **http://localhost:5000/docs** (disponível fora de `APP_ENV=production`).

1. **Cadastro** (opcional): `POST /api/v1/auth/register` → *Try it out* → edite o JSON → *Execute* → `201`.
2. **Login**: clique em **Authorize** (cadeado no topo). Em `username` vai o **email**, em `password` a senha.
   Client id/secret ficam vazios. Clique em *Authorize*.
3. Os endpoints com cadeado passam a enviar `Authorization: Bearer <token>` sozinhos. Teste com
   `GET /api/v1/auth/me` → `200`.
4. Para ver o `401`: **Authorize** → *Logout* e execute `GET /api/v1/auth/me` de novo.

A autorização fica salva no navegador (`persistAuthorization`), então recarregar a página não desloga.
O botão usa `POST /api/v1/auth/token` (padrão OAuth2), que chama o mesmo serviço de login do frontend
(mesma validação e mesmo rate limit).

**Inserir um usuário direto no MySQL** (ex.: para testes manuais). A senha precisa estar em bcrypt:

```bash
HASH=$(docker compose exec -T backend python -c "from app.core.security import hash_password; print(hash_password('Teste@123'))" | tr -d '')
docker compose exec -T mysql sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' <<SQL
INSERT INTO users (id, name, email, password_hash, city, is_active, is_admin, created_at, updated_at)
VALUES (UUID(), 'Usuário Teste', 'teste@medflux.com', '$HASH', 'Marília, SP', 1, 0, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));
SQL
```

Depois é só fazer login com `teste@medflux.com` / `Teste@123` pelo **Authorize**.

## Endpoints

Base: `http://localhost:5000/api/v1`. 🔒 = exige `Authorization: Bearer <token>`.

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/register` | — | Cadastro; devolve a sessão (`token` + `user`) |
| POST | `/auth/login` | — | Login (JSON); devolve a sessão |
| POST | `/auth/token` | — | Login OAuth2 (form `username`=email, `password`), usado pelo Swagger |
| GET | `/auth/me` | 🔒 | Usuário do token |
| GET | `/users/me` | 🔒 | Perfil (com URL pré-assinada da foto) |
| PUT | `/users/me` | 🔒 | Atualiza nome, email e/ou cidade |
| POST | `/users/me/avatar` | 🔒 | Envia foto (multipart, campo `file`) para o MinIO |
| GET | `/health/units?type=UPA\|UBS` | — | Unidades de saúde para o mapa |
| POST | `/triage/session` | 🔒 | Cria sessão de triagem (opcional: o 1º `/triage/message` cria automaticamente) |
| POST | `/triage/message` | 🔒 | Envia mensagem ao chat; resposta da Clara + recomendação |
| GET | `/triage/history` | 🔒 | Histórico de sessões (formato do dashboard) |
| GET | `/triage/session/{session_id}` | 🔒 | Sessão completa com as mensagens |
| POST | `/agents/history` | 🔒 | Registra evento de agente (MySQL + Qdrant) |
| GET | `/agents/history?limit=50` | 🔒 | Eventos de agentes do usuário |
| POST | `/vector/index-disease` | 🔒 admin | Indexa/atualiza doença na base de conhecimento |
| POST | `/vector/search` | 🔒 | Busca por similaridade |
| GET | `/files/{bucket}/{object_name}` | 🔒 | Baixa arquivo do próprio usuário |
| GET | `/healthz`, `/readyz` (fora do `/api/v1`) | — | Liveness e readiness |

Todos os erros têm o mesmo formato:

```json
{ "code": "invalid_credentials", "message": "Email ou senha inválidos.", "details": null }
```

Códigos usados: `400`, `401` (`unauthorized`, `invalid_token`, `invalid_credentials`), `403`, `404`,
`409` (`email_taken`, `session_exists`), `413`, `415`, `422` (`validation_error`, com a lista de campos
em `details`), `429` (`rate_limited`), `503` (`service_unavailable`) e `500` (`internal_error`, sem detalhes
internos). Toda resposta traz o header `X-Request-ID`, que também aparece nos logs.

## Exemplos de payload

**Cadastro** — `POST /auth/register`

```json
{ "name": "Marina Santos", "email": "marina.santos@medflux.com", "password": "123456", "city": "Marília, SP" }
```

**Login** — `POST /auth/login` → `200`

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "e8674bdb-afbd-43c2-b96c-9f3572b96331",
    "name": "Marina Santos",
    "email": "marina.santos@medflux.com",
    "city": "Marília, SP",
    "avatar_url": null,
    "avatarInitials": "MS",
    "created_at": "2026-10-13T22:43:53.456601"
  }
}
```

**Atualizar perfil** — `PUT /users/me`

```json
{ "name": "Marina Souza Santos", "city": "Bauru, SP" }
```

**Foto** — `POST /users/me/avatar`

```bash
curl -X POST http://localhost:5000/api/v1/users/me/avatar \
  -H "Authorization: Bearer $TOKEN" -F "file=@foto.png;type=image/png"
```

```json
{
  "bucket": "medflux-users",
  "object_name": "e8674bdb-.../avatar-55ec158f-....png",
  "content_type": "image/png",
  "size": 48213,
  "url": "http://localhost:9000/medflux-users/...?X-Amz-Signature=...",
  "expires_in": 3600
}
```

**Mensagem de triagem** — `POST /triage/message`

```json
{ "session_id": "a4ba5e14-229d-4da7-86e7-602e112d4cd6", "message": "Estou com febre alta e manchas vermelhas" }
```

```json
{
  "session_id": "a4ba5e14-229d-4da7-86e7-602e112d4cd6",
  "message_id": "0e5f64d8-6654-4899-b753-f658405066e2",
  "reply": "Entendi, Marina. Pelos sinais que você contou, o ideal é ser avaliado(a) presencialmente hoje.",
  "timestamp": "19:44",
  "triage_recommendation": {
    "required": true,
    "unit_type": "UPA",
    "urgency_label": "UPA - Atendimento Hoje",
    "title": "Procure uma UPA ainda hoje",
    "description": "Os sintomas indicam necessidade de avaliação presencial...",
    "warning": "Se a dor ficar insuportável, houver desmaio ou vômito contínuo, ligue 192."
  },
  "source": "fallback"
}
```

`source` indica quem gerou a resposta: `llm` (OpenRouter) ou `fallback` (regras locais).
`triage_recommendation` é `null` quando a mensagem não descreve sintomas (ex.: "oi").

**Histórico** — `GET /triage/history`

```json
[
  {
    "id": "a4ba5e14-229d-4da7-86e7-602e112d4cd6",
    "title": "Febre",
    "description": "Orientação para UPA • Hoje, 19:44",
    "timestamp": "Hoje, 19:44",
    "status": "Encaminhado para UPA",
    "route": "/chat",
    "status_code": "completed",
    "summary": "Sintomas relatados: febre, manchas na pele. Orientação: UPA - Atendimento Hoje.",
    "unit_type": "UPA",
    "created_at": "2026-10-13T22:44:25.753822",
    "updated_at": "2026-10-13T22:44:25.788974"
  }
]
```

**Unidades de saúde** — `GET /health/units`

```json
[{ "id": "upa-sul", "name": "UPA Sul", "type": "UPA", "address": "R. João Ramalho, 889 - Marília/SP",
   "latitude": -22.2244, "longitude": -49.9549, "position": [-22.2244, -49.9549] }]
```

**Indexar doença** (admin) — `POST /vector/index-disease`

```json
{
  "name": "Dengue",
  "description": "Arbovirose transmitida pelo Aedes aegypti.",
  "symptoms": ["febre alta", "dor atrás dos olhos", "manchas vermelhas"],
  "recommended_unit": "UPA",
  "severity": "urgente"
}
```

**Busca vetorial** — `POST /vector/search`

```json
{ "query": "febre alta e manchas vermelhas", "collection": "diseases", "limit": 3, "with_vector": false }
```

```json
{
  "query": "febre alta e manchas vermelhas",
  "collection": "diseases",
  "results": [
    { "id": "6f0c...", "collection": "diseases", "score": 0.3615, "vector": null,
      "payload": { "name": "Dengue", "symptoms": ["febre alta", "..."], "recommended_unit": "UPA", "text": "..." } }
  ]
}
```

**Evento de agente** — `POST /agents/history`

```json
{ "agent_name": "support_agent", "event_type": "note", "input_text": "Paciente pediu retorno", "output": {"ok": true} }
```

## Triagem, agentes e OpenRouter

Cada mensagem do chat passa por este fluxo (`services/agent_service.py`):

1. **Contexto**: últimas 20 mensagens da sessão (MySQL) + doenças semelhantes e relatos anteriores do
   próprio paciente (Qdrant).
2. **`symptoms_agent`**: extrai sintomas, sinais de alarme e gravidade (`emergencia`, `urgente`, `moderada`,
   `leve`, `indefinida`).
3. **`triage_agent`**: decide UPA x UBS e redige a resposta no formato `TriageRecommendation`.
4. **`summarizer_agent`**: resume a sessão (vai para `TriageSession.summary` e para o histórico).
5. **Persistência**: mensagens, `SymptomRecord` e um `AgentEvent` por agente no MySQL; a pergunta do
   paciente e os eventos indexados no Qdrant; a conversa concluída arquivada em JSON no bucket `medflux-triage`.

**Regras de segurança clínica**:

- Palavras-chave de alarme (dor no peito, falta de ar, desmaio, sinais de AVC, etc.) **sempre** levam à UPA.
  O LLM pode aumentar a gravidade, nunca diminuir. Uma resposta do LLM que mande para a UBS um caso com
  sinal de alarme é descartada e substituída pelo fallback.
- Sintomas citados em mensagens anteriores da sessão continuam valendo ("dor no peito" → "começou faz 1h").
- Resposta inválida, timeout, erro HTTP ou JSON malformado do LLM resultam no fallback determinístico,
  que tem a mesma estrutura. O chat nunca quebra por causa da IA.

**Configurar o OpenRouter**:

1. Crie uma chave em https://openrouter.ai/keys.
2. No `.env`: `OPENROUTER_API_KEY=sk-or-...` e, se quiser, outro `OPENROUTER_MODEL`
   (qualquer id da lista https://openrouter.ai/models, ex.: `anthropic/claude-sonnet-4.5`, `google/gemini-2.5-flash`).
3. Reinicie o backend. Em `/readyz`, `openrouter` passa de `fallback` para `configured`.

As chamadas usam `response_format: json_object`, `OPENROUTER_TIMEOUT` segundos de timeout e os headers
`HTTP-Referer`/`X-Title` recomendados pelo OpenRouter. Cada mensagem gera até 3 chamadas (sintomas, triagem, resumo).

**Trocar o runtime dos agentes** (`agents/runtime.py`):

| `AGENT_RUNTIME` | Como executa |
|---|---|
| `custom` (padrão) | cliente HTTP próprio (`integrations/openrouter_client.py`) |
| `ag2` | cada agente vira um `ag2.Agent` com `OpenAIConfig` apontando para o OpenRouter |

Agentes, serviços e endpoints não mudam: eles só conhecem a interface `AgentRuntime.complete()`.
Para adicionar outro framework, implemente essa interface e registre-o em `build_runtime`.

## Banco vetorial (Qdrant)

Coleções criadas automaticamente (similaridade cosseno, dimensão `EMBEDDING_DIM`):

| Coleção | Conteúdo | Escopo |
|---|---|---|
| `diseases` | base de conhecimento de doenças (seed com 13 condições comuns) | global |
| `symptoms` | reservada para catálogo de sintomas | global |
| `medical_context` | reservada para textos clínicos de apoio | global |
| `user_queries` | mensagens dos pacientes na triagem | por usuário |
| `agent_history` | eventos dos agentes | por usuário |

Cada item tem `id`, `collection`, `payload` (inclui `text`) e `vector`. Coleções por usuário são sempre
filtradas por `user_id`: a busca nunca devolve dados de outra pessoa. Doenças são gravadas no MySQL
(`disease_embeddings`, fonte de verdade) e no Qdrant com id estável, então reindexar atualiza em vez de duplicar.

**Embeddings**: hoje são gerados localmente (`utils/embeddings.py`, *feature hashing* de palavras, bigramas e
n-gramas de caracteres). Funciona offline, sem custo e de forma reprodutível, mas a similaridade é lexical.
Para similaridade semântica, troque `embed_text` por um modelo de embeddings, ajuste `EMBEDDING_DIM`, apague
as coleções e rode `python -m app.seed` novamente.

## Arquivos no MinIO

| Bucket | Conteúdo | Chave |
|---|---|---|
| `medflux-users` | fotos de perfil | `{user_id}/avatar-{uuid}.{ext}` |
| `medflux-triage` | conversas de triagem concluídas (JSON) | `{user_id}/{session_id}.json` |
| `medflux-documents` (`MINIO_BUCKET`) | documentos (reservado) | `{user_id}/...` |

- Buckets **privados**. O banco guarda apenas a chave do objeto (`users.avatar_key`).
- O perfil devolve `avatar_url` como **URL pré-assinada** (expira em `PRESIGNED_URL_EXPIRE_MINUTES`), que pode
  ir direto num `<img src>`. Ela é assinada com `MINIO_PUBLIC_ENDPOINT`, o host que o navegador enxerga.
- Alternativa autenticada: `GET /api/v1/files/{bucket}/{object_name}` com o token. O usuário só acessa
  objetos com o prefixo do próprio id. Path traversal (`..`) é bloqueado.
- Upload de avatar: no máximo 5 MB. O tipo é validado pelo conteúdo real do arquivo (assinatura JPEG, PNG
  ou WEBP), não pela extensão. Ao enviar uma foto nova, a antiga é removida.

## Integração com o frontend

O frontend (`../src/services/api.ts`) usa `http://localhost:5000/api/v1` por padrão (ou `VITE_API_URL`) e
envia o token salvo na sessão no header `Authorization`. Contratos atendidos sem alteração de tipos:

- `LoginResponse` → `{ token, user: { name, city, avatarInitials } }` (login e cadastro).
- `TriageMessageRequest/Response` → `session_id` gerado no navegador; a 1ª mensagem cria a sessão.
- `TriageHistoryItem` → `id, title, description, timestamp, status, route`.
- `HealthUnit` → `position: [lat, lng]`, `type: "UPA" | "UBS"`.
- Erros: o cadastro lê `message`.

CORS liberado para `FRONTEND_URL` (padrão `http://localhost:5173`, o Vite).

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Não precisam de Docker: SQLite em memória, Qdrant em modo local em memória (`AsyncQdrantClient(":memory:")`),
MinIO e Redis substituídos por dublês e o OpenRouter mockado com `httpx.MockTransport`.

| Arquivo | Cobre |
|---|---|
| `test_auth.py` | criação de usuário, login com senha correta e incorreta, validações, token inválido, rate limit, CORS |
| `test_users.py` | perfil, upload de avatar para o MinIO (troca e remoção da foto antiga), tipos e tamanho inválidos, acesso a arquivos |
| `test_triage.py` | criação de sessão, resposta de triagem com fallback (UPA/UBS/sem recomendação), histórico, privacidade entre usuários, unidades |
| `test_vector_service.py` | indexação e busca vetorial no Qdrant, isolamento por usuário, endpoints, permissão de admin |
| `test_agents.py` | integração com OpenRouter mockado, proteção contra rebaixar emergência, saída inválida do LLM, runtime AG2 |

## Segurança

- Senhas com **bcrypt** (custo 12); limite de 72 bytes validado. Login com email inexistente também
  executa o bcrypt, então o tempo de resposta não revela quais emails estão cadastrados. A mensagem de erro é a mesma nos dois casos.
- **JWT** HS256 com expiração (`ACCESS_TOKEN_EXPIRE_MINUTES`), claims `sub/iat/exp/type` obrigatórias e
  algoritmo fixo (não aceita `none`). A API não sobe sem `JWT_SECRET_KEY` de 32+ caracteres.
- **Rate limit** de login com Redis: após `LOGIN_MAX_ATTEMPTS` falhas, o email fica bloqueado por
  `LOGIN_LOCKOUT_SECONDS` (`429`).
- Todas as rotas de usuário exigem `Depends(get_current_user)`. Sessões, arquivos e vetores de outro usuário
  respondem `404`, sem revelar que existem. Indexar doenças exige `is_admin`.
- Validação de entrada com Pydantic em todos os endpoints. Uploads são validados pelo conteúdo real do arquivo.
- Nenhum segredo no código: tudo vem do `.env`, que não é versionado (nem copiado para a imagem, via `.dockerignore`).
- Container da API roda com usuário sem privilégios. Buckets do MinIO são privados.
- Erros `500` não expõem stack trace; o detalhe fica só no log, ligado ao `X-Request-ID`.
- Logs não registram senhas, tokens nem o conteúdo das mensagens de saúde.

**Antes de produção**: trocar todos os segredos, usar HTTPS (`MINIO_SECURE=true` e proxy TLS na API), criar
um usuário de serviço no MinIO em vez de usar o root, definir `QDRANT_API_KEY`, restringir as portas
expostas (MySQL/Redis/Qdrant não precisam ficar públicos) e `APP_ENV=production` (desliga o usuário demo).

## Decisões técnicas

- **FastAPI + SQLAlchemy async**: o chat espera respostas do LLM (I/O de segundos). Com async, uma requisição
  esperando o OpenRouter não bloqueia as outras. O MinIO, cujo SDK é síncrono, roda em `asyncio.to_thread`.
- **Camadas routes → services → repositories**: as regras ficam testáveis sem HTTP e os bancos podem ser
  trocados sem mexer nas regras (os testes trocam MySQL por SQLite e Qdrant por memória).
- **Fallback determinístico com a mesma estrutura do LLM**: o sistema funciona sem chave de API (demo,
  desenvolvimento, OpenRouter fora do ar) e o frontend não precisa tratar dois formatos.
- **Abstração `AgentRuntime`**: AG2 é um framework em evolução rápida (a 1.x mudou o pacote de `autogen` para `ag2`).
  Isolá-lo atrás de uma interface de um método permite trocar ou atualizar sem efeito nos endpoints.
- **Embeddings locais**: evitam custo e dependência externa para indexar e buscar. Mantêm a interface pronta
  para um modelo semântico.
- **IDs UUID em string**: o frontend já gera o id da sessão (`crypto.randomUUID`), e UUIDs não expõem a quantidade de registros.
- **Datas em UTC no banco**: exibidas no horário de Brasília (`BRT`, sem horário de verão desde 2019).
- **Redis opcional**: sem ele a API funciona normalmente, só sem rate limit.
