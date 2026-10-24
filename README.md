# Easy Assets — Backend

Backend do sistema de gestão de ativos do laboratório B-111, desenvolvido no Projeto Integrador IV do SENAI Roberto Mange.

O projeto utiliza **Python, Django e Django REST Framework (DRF)** para disponibilizar uma API REST compartilhada pelo painel web, desenvolvido em Vue.js, e pelo aplicativo mobile, desenvolvido em Flutter.

A API centraliza os dados, a autenticação e as regras de negócio, evitando a duplicação da lógica entre as duas aplicações clientes.

O desenvolvimento local utiliza SQLite e não depende da Azure. A publicação no Azure App Service faz parte do planejamento de implantação do projeto.

## Sumário

- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Módulos do sistema](#módulos-do-sistema)
- [Executando localmente](#executando-localmente)
- [Endpoints da API](#endpoints-da-api)
- [Autenticação e permissões](#autenticação-e-permissões)
- [Integração com Vue.js e Flutter](#integração-com-vuejs-e-flutter)
- [Testes](#testes)
- [Deploy na Azure](#deploy-na-azure)
- [Plano de trabalho e melhorias](#plano-de-trabalho-e-melhorias)

## Tecnologias

| Tecnologia | Utilização |
|---|---|
| Python | Linguagem do backend |
| Django | Framework web |
| Django REST Framework | Desenvolvimento da API REST |
| SQLite | Banco de dados local |
| SimpleJWT | Autenticação por tokens JWT |
| Django Admin | Administração de dados |
| Gunicorn | Servidor WSGI previsto para produção |
| Azure App Service | Hospedagem planejada para a API |

## Arquitetura

```text
                    ┌─────────────────────┐
                    │    Painel Web       │
                    │    Vue.js           │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │                     │
                    │    API REST         │
                    │    Django + DRF     │
                    │                     │
                    │  Contas e usuários  │
                    │  Autenticação JWT   │
                    │  Gestão de ativos   │
                    │  Categorias         │
                    │  Manutenção e logs  │
                    │                     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      SQLite         │
                    │   Banco de dados    │
                    └─────────────────────┘
                               ▲
                               │
                    ┌──────────┴──────────┐
                    │    Aplicativo       │
                    │    Flutter          │
                    └─────────────────────┘
```

O diagrama representa a arquitetura lógica. No ambiente de produção, a API será hospedada no Azure App Service, utilizando a configuração de banco de dados definida para o ambiente.

Os clientes web e mobile consomem os mesmos endpoints. A autorização das operações é responsabilidade do backend, independentemente da interface utilizada.

## Módulos do sistema

### 1. Contas e autenticação

O módulo `contas` é responsável pelos usuários, perfis e papéis de acesso.

Os papéis previstos no projeto são:

- `PROFESSOR`
- `ALUNO`
- `SUPORTE`

A autenticação utiliza JWT. Após o login, o cliente recebe tokens para realizar requisições autenticadas.

O endpoint `/api/contas/me/` permite consultar os dados do usuário autenticado e seu papel, informação útil para inicializar a sessão no painel web e no aplicativo mobile.

Conforme a configuração inicial descrita no projeto, novos usuários recebem o papel `ALUNO` por padrão, definido em `contas/signals.py`.

### 2. Gestão de ativos

O módulo `ativos` concentra o cadastro e a consulta dos equipamentos do laboratório B-111.

O modelo `Ativo` contempla:

- Tipo de equipamento.
- Descrição.
- Número de patrimônio, quando aplicável.
- Código QR gerado automaticamente.
- Sala ou localização.
- Status do ativo.
- Latitude e longitude reservadas para a atividade L5.2.

O modelo `HistoricoMovimentacao` registra eventos relacionados aos ativos, permitindo consultar seu histórico.

Os filtros previstos para a listagem incluem status, tipo, sala e código QR.

### 3. Categorias

O módulo de categorias faz parte da organização funcional do Easy Asset e da interface web, que possui telas para listagem e cadastro de categorias.

Os endpoints definitivos devem corresponder às rotas registradas no backend. Consulte a seção de endpoints para identificar o que ainda precisa ser confirmado no arquivo de URLs.

### 4. Ordens de manutenção

O módulo `ordens_manutencao` contempla o gerenciamento das ordens de manutenção dos ativos.

O modelo `OrdemManutencao` possui os seguintes campos:

- `ativo`: referência ao ativo relacionado.
- `descricao`: descrição do serviço.
- `responsavel`: responsável pela manutenção.
- `status`: situação da ordem.
- `custo_estimado`: custo previsto, quando informado.
- `data_abertura`: data de criação.
- `data_conclusao`: data de conclusão, quando aplicável.

Os status definidos no modelo são:

- `Pendente`
- `Em andamento`
- `Concluída`
- `Cancelada`

O modelo `LogOrdemManutencao` registra eventos associados às ordens, incluindo criação, alteração de status e outras atualizações. Os registros podem conter a ação realizada, a descrição, o status anterior, o novo status, o usuário responsável e a data do evento.

Esse histórico é utilizado para apoiar a consulta das alterações realizadas nas ordens e a integração com a tela de relatórios do painel Vue.

## Executando localmente

### Pré-requisitos

- Python compatível com as dependências do projeto.
- `pip`.
- Git, para clonar o repositório.

### 1. Clonar o repositório

```bash
git clone https://github.com/MiguelSantos1910/ProjetoIntegrador_Backend.git
cd ProjetoIntegrador_Backend
```

### 2. Criar e ativar o ambiente virtual

**Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Aplicar as migrações

```bash
python manage.py migrate
```

Se houver alterações nos modelos ainda sem migrações criadas, gere e aplique as migrações correspondentes:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Criar um superusuário

```bash
python manage.py createsuperuser
```

### 6. Popular os ativos de teste

```bash
python manage.py seed_ativos
```

O comando disponibiliza 16 ativos de teste, distribuídos em quatro tipos:

- 4 gabinetes.
- 4 monitores.
- 4 teclados.
- 4 mesas.

Os números de patrimônio provisórios devem ser substituídos pelos valores reais do inventário.

### 7. Iniciar o servidor

```bash
python manage.py runserver
```

Endereços locais padrão:

- API: `http://127.0.0.1:8000/`
- Django Admin: `http://127.0.0.1:8000/admin/`

No Django Admin, ajuste o perfil do superusuário para `PROFESSOR` caso precise testar operações que dependam desse papel.

## Endpoints da API

Os endpoints abaixo consolidam as rotas descritas na documentação do projeto e nas nossas conversas. Os caminhos devem ser conferidos nos arquivos `urls.py` para garantir que correspondam exatamente à versão atual do código.

### Autenticação

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/token/` | Autenticar usuário e obter tokens JWT |
| `POST` | `/api/token/refresh/` | Renovar o token de acesso |
| `GET` | `/api/contas/me/` | Consultar o usuário autenticado |

### Usuários

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/contas/usuarios/` | Listar usuários |
| `POST` | `/api/contas/usuarios/` | Criar usuário |
| `GET` | `/api/contas/usuarios/<id>/` | Consultar um usuário |
| `PUT` | `/api/contas/usuarios/<id>/` | Atualizar um usuário |
| `PATCH` | `/api/contas/usuarios/<id>/` | Atualizar parcialmente um usuário |
| `DELETE` | `/api/contas/usuarios/<id>/` | Excluir usuário |

Os métodos e caminhos específicos dependem do `ViewSet` e das rotas efetivamente registrados. Uma rota própria para alteração de senha só deve ser documentada após sua confirmação no código.

### Ativos

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/ativos/` | Listar ativos |
| `POST` | `/api/ativos/` | Cadastrar ativo |
| `GET` | `/api/ativos/<id>/` | Consultar detalhes de um ativo |
| `PUT` | `/api/ativos/<id>/` | Atualizar um ativo |
| `PATCH` | `/api/ativos/<id>/` | Atualizar parcialmente um ativo |
| `DELETE` | `/api/ativos/<id>/` | Excluir um ativo, conforme as permissões |

Filtros previstos para a listagem:

```http
GET /api/ativos/?tipo=monitor
GET /api/ativos/?status=disponivel
GET /api/ativos/?sala=B-111
GET /api/ativos/?codigo_qr=CODIGO_DO_ATIVO
```

Os valores devem corresponder às opções e aos campos aceitos pelo backend.

### Histórico de movimentações

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/historico/` | Consultar movimentações |
| `POST` | `/api/historico/` | Registrar uma movimentação |

A disponibilidade de operações de criação e as permissões aplicadas devem ser verificadas no código da API.

### Ordens de manutenção

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/ordens_manutencao/` | Listar ordens |
| `POST` | `/api/ordens_manutencao/` | Criar ordem |
| `GET` | `/api/ordens_manutencao/<id>/` | Consultar uma ordem |
| `PUT` | `/api/ordens_manutencao/<id>/` | Atualizar uma ordem |
| `PATCH` | `/api/ordens_manutencao/<id>/` | Atualizar parcialmente uma ordem |
| `DELETE` | `/api/ordens_manutencao/<id>/` | Excluir uma ordem, se permitido |
| `GET` | `/api/ordens_manutencao/<id>/logs/` | Consultar os logs de uma ordem |

O endpoint de logs corresponde à view `listar_logs_ordem`, associada ao modelo `LogOrdemManutencao`.

Os logs permitem consultar a criação da ordem, as mudanças de status e outras atualizações registradas pelo backend.

### Saúde da API

| Método | Endpoint | Situação |
|---|---|---|
| `GET` | `/api/health/` | Endpoint de verificação de disponibilidade descrito no projeto |

## Autenticação e permissões

Os endpoints protegidos devem receber o token JWT no cabeçalho HTTP:

```http
Authorization: Bearer <access_token>
```

O fluxo básico de autenticação é:

1. O cliente envia as credenciais para `/api/token/`.
2. A API retorna os tokens disponíveis.
3. O cliente utiliza o token de acesso nas requisições protegidas.
4. Quando necessário, o cliente solicita a renovação por `/api/token/refresh/`.
5. O cliente consulta `/api/contas/me/` para obter os dados do usuário autenticado.

A política provisória descrita para os ativos permite leitura a usuários autenticados e restringe operações de criação e edição a professores e usuários de suporte.

A aplicação de permissões deve ser verificada em todos os módulos, inclusive usuários, categorias, histórico e manutenção. Ocultar botões no frontend não substitui a autorização no servidor.

A atividade L4.1 prevê o reforço das regras de segurança.

## Integração com Vue.js e Flutter

### Painel web — Vue.js

O frontend deve centralizar as requisições em uma camada de API, responsável por configurar a URL base, enviar o token de acesso e tratar erros HTTP.

No Easy Asset, o painel inclui telas de ativos, manutenção, configurações e relatórios. A tela de relatórios também consulta o histórico de alterações das ordens de manutenção.

A exportação de relatórios em PDF realizada no frontend não exige, por si só, um endpoint de geração de PDF no backend.

### Aplicativo mobile — Flutter

O aplicativo deve consumir os mesmos endpoints da API, organizando o acesso aos dados em serviços ou repositórios e utilizando gerenciamento de estado para compartilhar as informações entre telas.

A sessão pode ser mantida por um gerenciador de estado, como `Provider`. A persistência dos tokens deve utilizar armazenamento adequado para credenciais, e as permissões devem continuar sendo verificadas pela API.

### Leitura de QR Code

A leitura do QR Code deve identificar o ativo pelo código cadastrado e consultar a API utilizando o filtro `codigo_qr`, desde que o formato esteja implementado e validado no backend.

## Testes automatizados

Execute os testes do Django com:

```bash
python manage.py test
```

Os testes básicos existentes servem como ponto de partida para a evolução da cobertura prevista nas atividades G2.1 e G2.3.

Casos recomendados para ampliar a cobertura:

- Autenticação com credenciais válidas e inválidas.
- Acesso a endpoints protegidos sem token.
- Consulta de ativos por usuário autenticado.
- Tentativa de cadastro por usuário com papel `ALUNO`.
- Tentativa de edição por usuário sem permissão.
- Validação dos filtros de ativos.
- Registro e consulta do histórico de movimentações.
- Criação e atualização de ordens de manutenção.
- Registro de logs após alterações de ordens.
- Tratamento de recursos inexistentes e dados inválidos.

A lista descreve os testes a verificar e desenvolver; a execução de `python manage.py test` é necessária para confirmar o resultado real.

## Deploy na Azure

A publicação está planejada para o Azure App Service, com execução da aplicação Django por Gunicorn.

O processo de implantação deve configurar:

- `SECRET_KEY`: chave secreta forte e armazenada de forma segura.
- `DEBUG=False`.
- `CORS_ALLOWED_ORIGINS`: origens autorizadas do painel web.
- Configuração do banco de dados.
- Dependências de produção.
- Comando de inicialização do servidor.
- Aplicação controlada das migrações.

O repositório descreve o uso de SQLite no ambiente de produção. A configuração de persistência e a compatibilidade do armazenamento precisam ser verificadas no App Service antes de considerar o deploy pronto.

### Considerações sobre SQLite

O caminho do arquivo do banco deve apontar para um local persistente, fora do diretório que é substituído durante as publicações.

A configuração de `DATABASE_URL`, isoladamente, não garante persistência: é necessário confirmar que o caminho está disponível e que o armazenamento foi configurado corretamente no ambiente.

SQLite pode apresentar limitações em ambientes com gravações concorrentes ou armazenamento de rede, incluindo erros como `database is locked`. Por isso, o deploy deve ser validado com testes de persistência, reinicialização e acesso concorrente.

Não mantenha chaves secretas ou credenciais diretamente no repositório.

## Plano de trabalho

| Atividade | Objetivo |
|---|---|
| L2.1 | Modelagem de dados, configuração inicial e preparação para deploy |
| L2.2 / L2.3 | Validação dos dados e do inventário de ativos |
| M2.2 | Integração do painel web com autenticação e identificação do usuário |
| G2.1 / G2.3 | Ampliação dos testes automatizados |
| L4.1 | Reforço de autenticação e permissões |
| L5.2 | Evolução dos recursos relacionados à localização dos ativos |

A situação de cada atividade deve ser atualizada de acordo com as entregas efetivamente concluídas.

## Próximas melhorias

- Validar as rotas e os métodos HTTP em todos os módulos.
- Garantir permissões consistentes por papel de usuário.
- Ampliar os testes automatizados de autenticação e autorização.
- Padronizar validações e respostas de erro.
- Documentar a API com OpenAPI/Swagger, caso a ferramenta esteja instalada.
- Validar o histórico de movimentações e os logs de manutenção.
- Testar a persistência dos dados no ambiente de produção.
- Automatizar e documentar o processo de implantação.

## Repositório

**Projeto:** Easy Assets — Projeto Integrador IV  
**Instituição:** SENAI Roberto Mange  
**Backend:** Django + Django REST Framework  
**Repositório:** https://github.com/MiguelSantos1910/ProjetoIntegrador_Backend
