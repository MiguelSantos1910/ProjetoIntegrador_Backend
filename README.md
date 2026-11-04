# Easy Asset — Backend

API do Easy Asset, o sistema de gestão de laboratórios e ativos do Projeto Integrador IV (ADS, SENAI Roberto Mange). É uma API REST em **Python, Django e Django REST Framework**, compartilhada pelo painel web (Vue.js) e pelo aplicativo mobile (Flutter).

A API concentra os dados, a autenticação, as permissões por papel e as regras de negócio. Os clientes só exibem e enviam dados: quem decide o que cada usuário pode fazer é sempre o back-end.

## Sumário

- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Módulos do sistema](#módulos-do-sistema)
- [Executando localmente](#executando-localmente)
- [Usuários de teste](#usuários-de-teste)
- [Papéis e permissões](#papéis-e-permissões)
- [Endpoints da API](#endpoints-da-api)
- [Segurança](#segurança)
- [Testes automatizados](#testes-automatizados)
- [Backup e restauração](#backup-e-restauração)
- [Publicação](#publicação)
- [Integração com o painel web e o app](#integração-com-o-painel-web-e-o-app)
- [Limitações conhecidas](#limitações-conhecidas)
- [Créditos e licenças](#créditos-e-licenças)
- [Repositórios](#repositórios)

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.11 | Linguagem do back-end |
| Django 5.2 | Framework web, ORM, migrações e Django Admin |
| Django REST Framework | API REST |
| SimpleJWT (com blacklist) | Autenticação por tokens JWT |
| django-filter | Filtros nas listagens |
| django-cors-headers | CORS para o painel web |
| django-environ | Configuração por variáveis de ambiente (`.env`) |
| SQLite | Banco de dados (local e produção, por decisão do professor) |
| Gunicorn e WhiteNoise | Servidor WSGI e arquivos estáticos em produção |
| GitHub Actions | Execução dos testes a cada push e pull request |

## Arquitetura

```text
   Painel web (Vue.js)          Aplicativo (Flutter)
            │                            │
            └──────────┬─────────────────┘
                       │  HTTP + JWT (Authorization: Bearer)
                       ▼
        ┌──────────────────────────────────┐
        │        API REST — Django + DRF   │
        │                                  │
        │  contas            login, papéis, auditoria
        │  ativos            ativos e histórico
        │  ordens_manutencao ordens e logs
        │  backups           backup e restauração
        └────────────────┬─────────────────┘
                         ▼
                SQLite (db.sqlite3)
```

É um monólito modular: cada app do Django é um módulo com seus modelos, serializers, views, permissões e testes. A autorização é feita em classes de permissão no back-end (`permissions.py` e verificações nas views), nunca só na interface.

## Estrutura do projeto

```text
ProjetoIntegrador_Backend/
├── config/              # settings, URLs principais e WSGI
├── contas/              # usuários, perfis (papéis), login, logout e auditoria
├── ativos/              # ativos, histórico de movimentações e seed_ativos
├── ordens_manutencao/   # ordens de manutenção e seus logs
├── backups/             # backup e restauração do banco (API e comandos)
├── docs/
│   ├── seguranca.md     # riscos, medidas, testes, recuperação e política
│   └── backup.md        # funcionamento do backup, cron e roteiro de evidência
├── .github/workflows/   # pipeline de testes (GitHub Actions)
├── .env.example         # variáveis de ambiente, sem segredos
├── requirements.txt
├── runtime.txt
└── startup.sh           # comando de inicialização (Gunicorn)
```

## Módulos do sistema

### Contas (`contas`)

- `Perfil`: papel de cada usuário (`PROFESSOR`, `SUPORTE` ou `ALUNO`). É criado automaticamente (`contas/signals.py`): superusuário vira `PROFESSOR`; os demais, `ALUNO`.
- `LogConta`: auditoria de cadastro, login, falhas, bloqueio, logout e backup.
- `TentativaLogin`: controle de tentativas. Depois de **5 senhas erradas** o login fica bloqueado por **3 minutos** para aquele usuário e IP.

### Ativos (`ativos`)

- `Ativo`: tipo (`GABINETE`, `MONITOR`, `TECLADO` ou `MESA`), descrição, número de patrimônio, **código QR** (UUID gerado pelo sistema e imutável), sala, status (`ATIVO`, `EM_MANUTENCAO`, `DEVOLVIDO` ou `INATIVO`) e datas de cadastro e atualização. Latitude e longitude estão reservadas para uma evolução futura.
- `HistoricoMovimentacao`: eventos do ativo, gravados pelo próprio sistema:

| Ação | Evento |
|---|---|
| Cadastrar o ativo | `CADASTRO` |
| Mudar o status para Em manutenção | `MANUTENCAO` |
| Mudar o status para Devolvido | `DEVOLUCAO` |
| Inativar | `INATIVO` |
| Sair de Inativo (para qualquer status) | `REATIVACAO` |
| Voltar para Ativo depois de manutenção ou devolução | `RETORNO` |

Ativos **não são excluídos**: o caminho é inativar, o que preserva o histórico.

As categorias são os quatro **tipos fixos** do modelo `Ativo`; não há API de categorias.

### Ordens de manutenção (`ordens_manutencao`)

- `OrdemManutencao`: ativo, descrição, responsável, status (`Pendente`, `Em andamento`, `Concluída` ou `Cancelada`), custo estimado, data de abertura e data de conclusão (preenchida ao concluir).
- `LogOrdemManutencao`: criação, mudança de status e atualização, com status anterior, novo status, usuário e data.

Ordens **não são excluídas**: o caminho é cancelar (status `Cancelada`).

### Backup (`backups`)

Backup e restauração do banco SQLite, pelo painel (somente professor) ou pelo terminal. Ver [Backup e restauração](#backup-e-restauração).

## Executando localmente

### Pré-requisitos

- Python 3.11
- `pip`
- Git

### Passo a passo

```bash
# 1. Clonar
git clone https://github.com/MiguelSantos1910/ProjetoIntegrador_Backend.git
cd ProjetoIntegrador_Backend

# 2. Ambiente virtual
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Dependências
pip install -r requirements.txt

# 4. Configuração (opcional no ambiente local)
cp .env.example .env              # sem o .env, o projeto usa SQLite e valores padrão

# 5. Banco de dados
python manage.py migrate

# 6. Dados de demonstração (16 ativos fictícios: 4 de cada tipo)
python manage.py seed_ativos

# 7. Usuários de teste (ver a próxima seção)

# 8. Servidor
python manage.py runserver
```

- API: `http://127.0.0.1:8000/api/`
- Django Admin: `http://127.0.0.1:8000/admin/`
- Verificação de disponibilidade: `http://127.0.0.1:8000/api/health/`

Para que o app no **emulador Android** ou num **celular na mesma rede** acesse a API local, rode `python manage.py runserver 0.0.0.0:8000`.

### Variáveis de ambiente

Todas estão em [`.env.example`](.env.example):

| Variável | Padrão | Em produção |
|---|---|---|
| `SECRET_KEY` | chave de desenvolvimento | chave forte e secreta |
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `*` | domínio ou IP do servidor |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | arquivo SQLite em disco persistente |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | `False` |
| `CORS_ALLOWED_ORIGINS` | vazio | endereço do painel web |
| `BACKUP_DIR` | `backups_banco/` | pasta em disco persistente |
| `BACKUP_MAX` | `10` | quantos backups manter de cada tipo |

## Usuários de teste

O sistema tem três papéis. Para a demonstração, crie uma conta de cada:

| Usuário sugerido | Papel | Uso na demonstração |
|---|---|---|
| `professor_teste` | `PROFESSOR` | Administração completa: usuários, auditoria e backup |
| `suporte_teste` | `SUPORTE` | Ativos e ordens de manutenção |
| `aluno_teste` | `ALUNO` | Somente consulta |

Use nomes de usuário em **minúsculas**: o app converte o usuário para minúsculas antes do login. As senhas **não ficam no repositório** e são entregues à banca separadamente.

Criação pelo terminal:

```bash
python manage.py createsuperuser --username professor_teste   # superusuário já nasce PROFESSOR

python manage.py shell -c "
from django.contrib.auth.models import User
for nome, papel in [('suporte_teste', 'SUPORTE'), ('aluno_teste', 'ALUNO')]:
    u = User.objects.create_user(nome, password=input(f'Senha de {nome}: '))
    u.perfil.papel = papel
    u.perfil.save()
"
```

Também é possível criar as contas pela tela de cadastro do painel (todas nascem `ALUNO`) e depois mudar o papel em **Perfis**, entrando como professor.

## Papéis e permissões

| Operação | Aluno | Suporte | Professor |
|---|:-:|:-:|:-:|
| Consultar ativos, histórico e ordens | ✅ | ✅ | ✅ |
| Cadastrar, editar e inativar ativos | ❌ | ✅ | ✅ |
| Abrir, atualizar e cancelar ordens | ❌ | ✅ | ✅ |
| Excluir ativos, ordens ou histórico | ❌ | ❌ | ❌ |
| Ver a lista de usuários | só a própria conta | só a própria conta | ✅ |
| Alterar papel, nome ou e-mail de usuários | ❌ | ❌ | ✅ |
| Trocar a própria senha | ✅ | ✅ | ✅ |
| Consultar a auditoria de contas | ❌ | ❌ | ✅ |
| Gerar, baixar e restaurar backups | ❌ | ❌ | ✅ |

Operações não permitidas retornam `403`; sem token, `401`. O superusuário tem as mesmas permissões do professor.

## Endpoints da API

Todos exigem `Authorization: Bearer <access>`, exceto os marcados como públicos.

### Autenticação

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/token/` | Login (público). Retorna `access` e `refresh`; grava `LOGIN` ou `LOGIN_FALHA` |
| `POST` | `/api/token/refresh/` | Renova o token (público). O refresh é rotacionado e o antigo é invalidado |
| `POST` | `/api/contas/logout/` | Logout. Corpo `{"refresh": "..."}`; invalida o refresh e grava `LOGOUT` |
| `GET` | `/api/contas/me/` | Dados e papel do usuário autenticado |

### Usuários e auditoria

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/contas/usuarios/` | Cadastro (público). Sempre cria `ALUNO`; valida a força da senha |
| `GET` | `/api/contas/usuarios/` | Lista (professor vê todos; os demais, só a própria conta) |
| `GET` | `/api/contas/usuarios/<id>/` | Consulta um usuário |
| `PATCH` / `PUT` | `/api/contas/usuarios/<id>/` | Edita usuário e papel (somente professor) |
| `DELETE` | `/api/contas/usuarios/<id>/` | Exclui usuário (somente professor, nunca a própria conta) |
| `PATCH` | `/api/contas/usuarios/<id>/senha/` | Troca de senha. Corpo `{"password": "..."}` (o próprio usuário ou professor) |
| `GET` | `/api/contas/auditoria/` | Auditoria de contas (somente professor). Filtros `?usuario=<id>` e `?tipo_evento=LOGIN` |

### Ativos e histórico

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/ativos/` | Lista. Filtros `?status=`, `?tipo=`, `?sala=` e `?codigo_qr=` |
| `POST` | `/api/ativos/` | Cadastra (o código QR é gerado pelo sistema); grava `CADASTRO` |
| `GET` | `/api/ativos/<id>/` | Detalhe com o histórico |
| `PATCH` / `PUT` | `/api/ativos/<id>/` | Atualiza; mudar o status grava o evento no histórico |
| `DELETE` | `/api/ativos/<id>/` | Bloqueado (`403`): inative com `PATCH {"status": "INATIVO"}` |
| `GET` | `/api/historico/` | Histórico. Filtros `?ativo=<id>` e `?tipo_evento=` |
| `POST` / `PATCH` / `DELETE` | `/api/historico/...` | Bloqueados (`403`): o histórico é gravado pelo sistema |

Exemplos de filtro:

```http
GET /api/ativos/?tipo=MONITOR
GET /api/ativos/?status=EM_MANUTENCAO
GET /api/ativos/?sala=B-111
GET /api/ativos/?codigo_qr=0147fe01-1ef0-4bf9-8cf5-4345907cd036
```

### Ordens de manutenção

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/ordens_manutencao/` | Lista |
| `POST` | `/api/ordens_manutencao/` | Abre ordem (professor e suporte); grava o log `Criada` |
| `GET` | `/api/ordens_manutencao/<id>/` | Consulta |
| `PATCH` / `PUT` | `/api/ordens_manutencao/<id>/` | Atualiza; mudar o status grava o log. Para cancelar: `{"status": "Cancelada"}` |
| `DELETE` | `/api/ordens_manutencao/<id>/` | Bloqueado (`403`) |
| `GET` | `/api/ordens_manutencao/<id>/logs/` | Logs da ordem (somente leitura) |

### Backup e outros

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/backups/` | Lista os backups (somente professor) |
| `POST` | `/api/backups/` | Gera um backup (somente professor) |
| `POST` | `/api/backups/<nome>/restaurar/` | Restaura. Corpo `{"confirmacao": "RESTAURAR"}` (somente professor) |
| `GET` | `/api/backups/<nome>/download/` | Baixa o arquivo do backup; grava `BACKUP_BAIXADO` (somente professor) |
| `GET` | `/api/health/` | Verificação de disponibilidade (público) |

## Segurança

Resumo do que está implementado. A lista completa de riscos, medidas, casos de mau uso, modelo de ameaça (STRIDE), recuperação (RPO e RTO), LGPD e a política de segurança estão em [`docs/seguranca.md`](docs/seguranca.md).

- **Autenticação JWT** em todas as rotas, exceto login, renovação, cadastro e health.
- **Senhas** validadas pelo Django e guardadas com hash; nunca aparecem em log.
- **Bloqueio** após 5 tentativas erradas, por 3 minutos.
- **RBAC** no back-end para ativos, ordens, usuários, auditoria e backup.
- **Rastreabilidade:** nada é excluído; histórico e logs são somente leitura.
- **Auditoria** de cadastro, login, falha, bloqueio, logout e backup.
- **Sessão:** refresh rotacionado, com blacklist e invalidado no logout.
- **Backup** com restauração testada e download registrado na auditoria.
- **Segredos** fora do Git (`.env`, banco e backups no `.gitignore`).

## Testes automatizados

```bash
python manage.py test               # todos
python manage.py test contas        # só um app
```

São **43 testes**:

| App | O que cobre |
|---|---|
| `contas` | Login correto e errado, bloqueio na 5ª tentativa, logout que invalida o refresh, cadastro sempre `ALUNO`, senha fraca, senha fora do log, escalada de privilégio, troca de senha de outra pessoa e acesso à auditoria |
| `ativos` | Cadastro com histórico, eventos de cada mudança de status, aluno sem permissão de escrita, ativo sem exclusão, histórico imutável e busca pelo código QR |
| `ordens_manutencao` | Permissões por papel, log de criação e de status, data de conclusão, cancelamento, status inválido, ordem sem exclusão e logs somente leitura |
| `backups` | Acesso por papel, geração, download (com log e só pelo professor), limite de arquivos, confirmação obrigatória, nome inválido, restauração e desfazer a restauração |

O workflow [`.github/workflows/testes.yml`](.github/workflows/testes.yml) roda `makemigrations --check` e os testes em todo push para o `main` e em todo pull request.

## Backup e restauração

```bash
python manage.py backup_banco                               # gera um backup
python manage.py restaurar_banco                            # lista os backups
python manage.py restaurar_banco db_AAAAMMDD_HHMMSS.sqlite3 # restaura (pede "RESTAURAR")
```

Também pelo painel web, na tela **Backup** (somente professor), que permite gerar, **baixar** e restaurar. Os arquivos ficam em `BACKUP_DIR`, fora do Git, e o estado atual é salvo automaticamente antes de cada restauração. Restaurar volta **o banco inteiro** à data do backup, inclusive usuários e logs.

O arquivo baixado contém os hashes de senha de todos os usuários: guarde-o em local privado, nunca no Git. Cada download fica registrado na auditoria (`BACKUP_BAIXADO`).

Detalhes, agendamento diário (cron) e roteiro de evidência com prints: [`docs/backup.md`](docs/backup.md).

## Publicação

A instância publicada usada pelo app mobile roda num servidor na AWS, em `http://54.20.29.135/api`. Para produção, o projeto usa Gunicorn (comando em `startup.sh`). O repositório também traz a configuração para o Azure App Service (`WEBSITE_HOSTNAME` é aceito em `ALLOWED_HOSTS` automaticamente).

Em qualquer servidor:

1. Atualize o código com o `main` e rode `pip install -r requirements.txt` e `python manage.py migrate`.
2. Defina as variáveis de produção (tabela acima): `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS` e `CORS_ALLOWED_ORIGINS`.
3. Aponte `DATABASE_URL` e `BACKUP_DIR` para um **disco persistente**, fora da pasta substituída a cada deploy.
4. Agende o backup diário (ver `docs/backup.md`).
5. Rode `python manage.py check --deploy` e trate os avisos.
6. Publique com **HTTPS**. Hoje o servidor responde em HTTP (risco R9 em `docs/seguranca.md`).

O SQLite atende o MVP, mas tem limite para muitas gravações simultâneas (`database is locked`).

## Integração com o painel web e o app

- **Painel web (Vue.js):** configure `VITE_APP_API_URL` no `.env` do front, por exemplo `http://127.0.0.1:8000/api`. Para ver os mesmos dados do app, use a URL do servidor publicado.
- **App (Flutter):** a URL padrão é a do servidor publicado. Para a API local: `flutter run --dart-define=API_URL=http://10.0.2.2:8000/api` (emulador).
- **QR Code:** o app lê o `codigo_qr` e consulta `GET /api/ativos/?codigo_qr=<código>`.
- **Movimentação pelo app:** mude o status do ativo com `PATCH /api/ativos/<id>/`. O histórico é gravado pelo back, e `POST /api/historico/` é bloqueado.

## Limitações conhecidas

- Sem HTTPS no servidor publicado (R9) e configuração de produção ainda padrão (R10).
- Mudança de papel e de senha ainda não gera evento de auditoria.
- Sem paginação nas listagens e sem versão na URL da API (`/v1`).
- Setor e laboratório são o campo de texto `sala`, sem cadastro próprio.
- As categorias são os tipos fixos do modelo.
- Mudança de sala não gera evento no histórico.

## Créditos e licenças

Bibliotecas usadas, todas de código aberto: Django (BSD-3-Clause), Django REST Framework (BSD-3-Clause), SimpleJWT (MIT), django-filter (BSD-3-Clause), django-cors-headers (MIT), django-environ (MIT), Gunicorn (MIT) e WhiteNoise (MIT).

Os dados de demonstração (`seed_ativos`) são fictícios.

## Repositórios

| Parte | Repositório |
|---|---|
| Back-end (este) | https://github.com/MiguelSantos1910/ProjetoIntegrador_Backend |
| Painel web | https://github.com/MiguelSantos1910/ProjetoIntegrador_Frontend |
| Aplicativo mobile | https://github.com/LANDOSOUZA/pi4-mobile-lando |

**Projeto:** Easy Asset, Projeto Integrador IV, ADS, SENAI Roberto Mange.
