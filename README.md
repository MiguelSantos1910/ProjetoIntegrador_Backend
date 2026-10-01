# Easy_Assets — Backend (Django + DRF)

Backend do sistema de gestão de ativos do laboratório B-111 (SENAI Roberto
Mange, Projeto Integrador IV). Expõe uma API REST única que tanto o painel
web (Miguel, Vue) quanto o app mobile (Flutter) vão consumir.

Isto é o ponto de partida da atividade **L2.1** do plano de trabalho
(modelagem de dados + configuração inicial do projeto + base para o deploy
na Azure). Roda 100% local com SQLite — não precisa da Azure para começar a
desenvolver.

## Como rodar local

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser  # crie um usuário para testar o /admin e a API
python manage.py seed_ativos      # popula os 16 ativos de teste (4 de cada tipo, sala B-111)

python manage.py runserver
```

Depois de criar o superusuário, entre em `/admin/`, abra **Contas → Perfis**
e ajuste o papel dele para `PROFESSOR` (por padrão todo usuário novo nasce
como `ALUNO` — veja `contas/signals.py`).

## O que já está pronto

- **Modelo de dados** (`ativos/models.py`): `Ativo` (tipo, descrição, número
  de patrimônio — nulo para teclados, `codigo_qr` gerado automaticamente,
  sala, status, latitude/longitude já reservados para a atividade L5.2 de
  mapa) e `HistoricoMovimentacao` (histórico de eventos de cada ativo, usado
  na tela de Detalhes do Equipamento).
- **Autenticação por papel** (`contas/models.py`): três papéis — professor,
  aluno, suporte técnico — via JWT (`/api/token/`).
- **API REST completa** de ativos e histórico, com filtros por `status`,
  `tipo`, `sala` e `codigo_qr` (é isso que o app usa depois de ler o QR
  Code físico do equipamento).
- **Permissão provisória**: qualquer usuário logado lê; só professor/suporte
  cria e edita. Vai ser reforçada de verdade na atividade **L4.1** (Sprint
  de Segurança) — o comentário em `ativos/permissions.py` marca isso.
- **Seed de dados de teste** batendo com o escopo real do projeto (4
  gabinetes, 4 monitores, 4 teclados, 4 mesas).
- Testes automatizados básicos (`python manage.py test`) como ponto de
  partida para o plano de testes do Guilherme (G2.1/G2.3).

## Principais endpoints

| Método | Endpoint | O que faz |
|---|---|---|
| POST | `/api/token/` | Login — recebe `username`/`password`, devolve `access`/`refresh` (JWT) |
| POST | `/api/token/refresh/` | Renova o token de acesso |
| GET | `/api/contas/me/` | Dados do usuário logado + papel |
| GET/PATCH/UPDATE/DELETE | `/api/contas/usuario` | Consulta, cria, deleta ou atualiza os usuários |
| GET/POST | `/api/ativos/` | Listar (com filtros `?tipo=`, `?status=`, `?sala=`, `?codigo_qr=`) / cadastrar ativo |
| GET/PATCH/DELETE | `/api/ativos/<id>/` | Detalhe (com histórico incluso) / editar / remover |
| GET/POST | `/api/historico/` | Consultar ou lançar um evento de movimentação |
| GET | `/api/health/` | Ping simples, útil para checar se o deploy na Azure está de pé |

Todo endpoint (exceto `/api/health/` e `/api/token/`) exige o header
`Authorization: Bearer <token>`.

## Deploy na Azure

O professor definiu que o banco de produção também é **SQLite** (mesmo
motor do ambiente local) — então não precisa provisionar nenhum banco
separado, só o App Service. Resumo dos passos (via Azure CLI; dá pra fazer
os mesmos passos pelo Portal, na aba "Deployment Center"):

```bash
# 1. Grupo de recursos e plano (B1 é barato; use F1 se o plano gratuito aceitar)
az group create --name easyassets-rg --location brazilsouth
az appservice plan create --name easyassets-plan --resource-group easyassets-rg --sku B1 --is-linux

# 2. O Web App em si, já apontando pro runtime Python
az webapp create --name easyassets-backend --resource-group easyassets-rg \
  --plan easyassets-plan --runtime "PYTHON:3.11"

# 3. Variáveis de ambiente (equivalente ao .env, mas nas configurações do app)
az webapp config appsettings set --name easyassets-backend --resource-group easyassets-rg --settings \
  SECRET_KEY="troque-por-uma-chave-grande-e-aleatoria" \
  DEBUG="False" \
  DATABASE_URL="sqlite:////home/data/db.sqlite3" \
  CORS_ALLOWED_ORIGINS="https://<url-do-painel-web-do-miguel>" \
  SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# 4. Comando de inicialização (mesmo conteúdo do startup.sh deste repositório)
az webapp config set --name easyassets-backend --resource-group easyassets-rg \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 config.wsgi"

# 5. Conectar o deploy a este repositório GitHub (ou use o Deployment Center no Portal)
az webapp deployment source config --name easyassets-backend --resource-group easyassets-rg \
  --repo-url https://github.com/MiguelSantos1910/ProjetoIntegrador_Backend --branch main --manual-integration
```

Pontos importantes:

- **`DATABASE_URL=sqlite:////home/data/db.sqlite3`** (repare nas 4 barras)
  é obrigatório — sem isso, o arquivo do banco fica dentro de
  `/home/site/wwwroot`, que é apagado e recriado a cada novo deploy, e
  vocês perderiam os dados cadastrados toda vez que subissem uma atualização.
- O arquivo `.deployment` deste repositório já manda a Azure rodar
  `collectstatic` e `migrate` automaticamente a cada deploy — não precisa
  fazer isso manualmente.
- SQLite na Azure App Service tem uma limitação conhecida: o
  armazenamento persistente é um compartilhamento de rede, que não lida
  bem com o travamento de arquivo que o SQLite usa para escrever. Para o
  volume de uso de um projeto acadêmico isso tende a não aparecer, mas se
  o log mostrar `database is locked`, é essa a causa — não é bug do código.
- Assim que o painel web do Miguel tiver uma URL, atualize
  `CORS_ALLOWED_ORIGINS` com ela (senão o navegador bloqueia as chamadas
  à API por causa do CORS).

## Próximos passos (conforme o Plano de Trabalho)

- **L2.2 / L2.3** já estão cobertos por este esqueleto — falta só ajustar
  os dados reais do inventário (trocar os placeholders `PAT-...` do
  `seed_ativos.py` pelos números de patrimônio verdadeiros).
- **Deploy na Azure** (resto da L2.1): seguir os passos da seção acima.
- **M2.2** (Miguel): já dá pra apontar o Vue para `POST /api/token/` e
  `GET /api/contas/me/` para montar a tela de login.
- **G2.1/G2.3** (Guilherme): `ativos/tests.py` é o ponto de partida do
  plano de testes — os casos de autenticação e CRUD básico já estão
  cobertos, faltam os casos de borda (ex.: usuário aluno tentando cadastrar
  ativo deve dar 403).
