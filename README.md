# face-temphora

API de **reconhecimento facial** para identificação de colaboradores. Recebe a foto de uma pessoa e responde quem é (entre os cadastrados de uma empresa) com base em embeddings faciais.

Construído com **FastAPI**, **InsightFace** (modelo `buffalo_l`, ArcFace ResNet-50) e **MySQL**. Pensado pra rodar em container, com deploy direto no **Cloud Run** (GCP).

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Stack](#stack)
- [Como rodar](#como-rodar)
- [Endpoints](#endpoints)
- [Banco de dados](#banco-de-dados)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Deploy no GCP](#deploy-no-gcp-cloud-run)
- [Como funciona o reconhecimento](#como-funciona-o-reconhecimento)

---

## Funcionalidades

- **Cadastrar embedding** de um colaborador a partir de uma foto (`POST /embedding`).
- **Identificar** uma pessoa em uma foto entre os colaboradores de uma empresa (`POST /match`).
- Aceita imagens em **JPEG, PNG, WebP, HEIC e HEIF** (HEIC do iPhone é convertido pra JPEG automaticamente).
- Detecção e validação de face (rejeita imagens sem face com `422`).

---

## Arquitetura

```
app/
├── app.py                       Entry point — cria a aplicação FastAPI
├── config/                      Configuração (lê .env, valida tipos)
│   └── env_config.py            
├── database/                    Camada de acesso ao MySQL
│   ├── connexao.py              Pool de conexões + suporte a SSL/TLS
│   └── models/                  CRUD por entidade
│       ├── update_embedding.py  
│       └── select_embedding.py  
├── routes/                      Camada HTTP (rotas FastAPI)
│   ├── embedding.py             POST /embedding — cadastrar
│   ├── match.py                 POST /match — identificar
│   ├── _upload_pipeline.py      Helper compartilhado (validar+ler+inferir)
│   └── index.py                 Registro central de routers
└── services/                    Lógica de negócio (sem dependência de FastAPI)
    ├── image_service.py         HEIC → JPEG, validação de mime
    ├── embedding_service.py     Inferência InsightFace (singleton)
    └── match_service.py         Busca + comparação por cosseno
```

### Fluxo de uma requisição

```
Cliente → POST /match (foto + id_empresa)
   │
   ▼
[routes/match.py]                      ── camada HTTP
   │ valida multipart, chama upload_to_faces()
   ▼
[routes/_upload_pipeline.py]           ── adapter HTTP↔services
   │ image_service.normalize_image_bytes()  → HEIC vira JPEG
   │ embedding_service.extract_embeddings() → InsightFace gera 512-d
   ▼
[services/match_service.py]            ── lógica pura
   │ select_embedding(id_empresa)      → consulta o MySQL
   │ cosine_similarity(candidato, ...) → para cada colaborador
   ▼
{match: true, id_colaborador: 7, similarity: 0.78}
```

A separação entre **rotas**, **services** e **database/models** mantém a lógica de negócio testável e independente do framework HTTP.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Reconhecimento facial | InsightFace (`buffalo_l`) + ONNXRuntime |
| Manipulação de imagem | OpenCV (headless), Pillow, pillow-heif |
| Banco de dados | MySQL 8 (driver `mysql-connector-python`, com pool) |
| Configuração | python-dotenv |
| Container | Docker (multi-stage), Docker Compose |

---

## Como rodar

### Pré-requisitos

- Docker + Docker Compose, **OU**
- Python 3.13+ e MySQL 8 instalados localmente

### Opção 1 — Docker Compose (recomendado pra dev)

Sobe a app + MySQL com um comando só:

```bash
cp .env.example .env
docker compose up --build
```

A primeira execução demora (~5–10 min) porque:
1. Instala dependências Python (insightface puxa muita coisa).
2. Pré-baixa o modelo `buffalo_l` (~280MB) durante o build.

Depois disso, fica tudo cacheado. A API sobe em `http://localhost:5011`.

```bash
# logs
docker compose logs -f app

# parar
docker compose down

# limpar tudo (inclusive volume do MySQL)
docker compose down -v
```

### Opção 2 — Localmente, sem Docker

```bash
# venv
python -m venv venv
source venv/bin/activate

# deps
pip install -r requirements.txt

# .env
cp .env.example .env
# edite as credenciais do MySQL

# subir
uvicorn app.app:app --host 0.0.0.0 --port 5011
```

A primeira requisição vai baixar o modelo `buffalo_l` (~280MB) automaticamente para `~/.insightface/models/buffalo_l/`.

### Documentação interativa

Com a app no ar, abra:

- **Swagger**: http://localhost:5011/docs
- **ReDoc**: http://localhost:5011/redoc

---

## Endpoints

### `GET /health`

Healthcheck simples.

```bash
curl http://localhost:5011/health
# {"status": "ok"}
```

### `POST /embedding` — Cadastrar embedding

Recebe uma foto e o `id_colaborador`, gera o embedding facial e salva no banco.

```bash
curl -X POST http://localhost:5011/embedding \
     -F "file=@foto.jpg" \
     -F "id_colaborador=42"
```

**Resposta:**

```json
{
  "id_colaborador": 42,
  "det_score": 0.87,
  "saved": true
}
```

**Erros possíveis:**
- `415` — formato de arquivo não suportado.
- `422` — nenhuma face detectada na imagem.
- `500` — falha ao salvar no banco.

### `POST /match` — Identificar colaborador

Recebe uma foto e o `id_empresa`, busca entre os colaboradores cadastrados e retorna o que mais bate.

```bash
curl -X POST http://localhost:5011/match \
     -F "file=@foto.jpg" \
     -F "id_empresa=1"
```

**Parâmetro opcional via query**: `threshold` (default `0.42`, faixa `[0, 1]`).

```bash
curl -X POST "http://localhost:5011/match?threshold=0.5" \
     -F "file=@foto.jpg" -F "id_empresa=1"
```

**Resposta:**

```json
{
  "match": true,
  "similarity": 0.78,
  "threshold": 0.42,
  "id_colaborador": 7,
  "best_id_colaborador": 7,
  "candidates_count": 12
}
```

| Campo | Descrição |
|---|---|
| `match` | `true` se passou do threshold. |
| `similarity` | Cosseno entre embeddings (`0` a `1`). |
| `id_colaborador` | ID do match (só populado se `match=true`). |
| `best_id_colaborador` | Quem foi mais parecido — útil pra debug mesmo abaixo do threshold. |
| `candidates_count` | Quantos colaboradores válidos foram comparados. |

**Erros possíveis:**
- `404` — empresa não tem nenhum colaborador com embedding cadastrado.
- `415` — formato não suportado.
- `422` — nenhuma face detectada.
- `503` — falha ao consultar o banco.

---

## Banco de dados

### Schema esperado

```sql
CREATE TABLE colaborador (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    id_empresa  INT NOT NULL,
    embedding   JSON NULL,
    INDEX idx_empresa (id_empresa)
);
```

A coluna `embedding` guarda o vetor de 512 floats serializado em JSON.

> **Sobre o tipo da coluna:** `JSON` ou `TEXT` funcionam (~9KB por linha). Para escalar (>10k colaboradores), considere migrar para `VARBINARY(2048)` armazenando bytes float32 — economiza ~5x em espaço e é mais rápido. Veja a discussão de trade-offs nos comentários do projeto.

---

## Variáveis de ambiente

Defina em `.env` (vide `.env.example`):

| Variável | Default | Descrição |
|---|---|---|
| `MYSQL_HOST` | `localhost` | Host do MySQL. |
| `MYSQL_PORT` | `3306` | Porta. |
| `MYSQL_USER` | `root` | Usuário. |
| `MYSQL_PASSWORD` | `` | Senha. |
| `MYSQL_DATABASE` | `face_temphora` | Nome do schema. |
| `MYSQL_SSL` | `false` | Ativa SSL/TLS na conexão. Sempre `true` em produção. |
| `MYSQL_SSL_REJECT_UNAUTHORIZED` | `true` | Valida o certificado do servidor. Mantenha `true` em produção. |

---

## Deploy no GCP (Cloud Run)

### Pré-requisitos

- Projeto na GCP com APIs habilitadas: `run.googleapis.com`, `cloudbuild.googleapis.com`, `artifactregistry.googleapis.com`, `sqladmin.googleapis.com`.
- Instância de **Cloud SQL (MySQL 8)** criada.
- `gcloud` CLI configurado (`gcloud auth login`, `gcloud config set project ...`).

### Deploy direto do código (build na nuvem)

```bash
PROJECT_ID=meu-projeto
REGION=southamerica-east1
SERVICE=face-temphora
INSTANCE_IP=34.X.X.X   # IP público do Cloud SQL

gcloud run deploy $SERVICE \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 60 \
  --concurrency 10 \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "MYSQL_HOST=$INSTANCE_IP,MYSQL_USER=app_user,MYSQL_DATABASE=temphora,MYSQL_SSL=true,MYSQL_SSL_REJECT_UNAUTHORIZED=true" \
  --set-secrets "MYSQL_PASSWORD=mysql-password:latest"
```

### Configurações importantes

| Flag | Por quê |
|---|---|
| `--memory 2Gi` | InsightFace + ONNXRuntime ocupa ~1GB em memória. |
| `--cpu 2` | Inferência usa todos os cores disponíveis. |
| `--concurrency 10` | CPU-bound, não vale subir muito. |
| `--min-instances 0` | Cobra zero quando ninguém usa (cold start ~10s). Para produção crítica, suba pra 1. |
| `MYSQL_SSL=true` | Cloud SQL exige TLS quando exposto via IP público. |

### Senha no Secret Manager

Em vez de passar a senha como env var (visível no console), use o Secret Manager:

```bash
echo -n "minha_senha" | gcloud secrets create mysql-password --data-file=-

# Dá permissão pra Service Account do Cloud Run ler o secret
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding mysql-password \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor
```

---

## Como funciona o reconhecimento

### Pipeline geral

1. **Upload** da imagem em `multipart/form-data`.
2. **Validação** do tipo (jpeg/png/webp/heic/heif).
3. **Conversão HEIC→JPEG** se necessário (Pillow + pillow-heif).
4. **Detecção de face** (SCRFD, dentro do InsightFace).
5. **Extração de embedding** — vetor de **512 dimensões**, L2-normalizado, gerado pelo modelo ArcFace ResNet-50 (`buffalo_l`).
6. **Comparação por similaridade de cossenos** com os embeddings do banco.

### Sobre o threshold

O `threshold` é o limite mínimo de similaridade pra considerar "mesma pessoa". Para o `buffalo_l`:

| Similaridade | Interpretação |
|---|---|
| `< 0.2` | Pessoas claramente diferentes. |
| `0.2 – 0.4` | Zona cinzenta — possivelmente diferentes. |
| `0.4 – 0.5` | Provavelmente a mesma pessoa. |
| `> 0.5` | Mesma pessoa com alta confiança. |
| `> 0.7` | Praticamente certo. |

Default do projeto: **`0.42`**. Pra MVP/autenticação, pode-se subir pra `0.5` (menos falsos positivos).

### Por que L2-normalizado?

Como ambos os vetores (do banco e da foto enviada) são normalizados (`||v|| = 1`), a similaridade de cossenos vira simplesmente `dot(a, b)` — operação extremamente rápida em numpy.

### Múltiplas faces na mesma foto

Quando a imagem tem várias faces, a rota `/match` compara **todas** elas com cada colaborador e retorna o **par com maior similaridade**. Isso permite identificar uma pessoa numa foto de grupo, por exemplo.
