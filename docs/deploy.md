# Publicação: PythonAnywhere (API) + Vercel (painel)

Guia para publicar o Easy Asset sem custo e com HTTPS:

| Parte | Onde | Endereço final (exemplo) |
|---|---|---|
| API Django | PythonAnywhere (plano gratuito) | `https://SEUUSUARIO.pythonanywhere.com/api/` |
| Painel Vue | Vercel (plano gratuito) | `https://easy-asset.vercel.app` |
| App Flutter | APK apontando para a API | — |

Por que essa combinação:

- O back usa **SQLite** e grava **backups em arquivo**: precisa de disco
  persistente. O PythonAnywhere mantém os arquivos entre reinícios e deploys.
- Painel em HTTPS só consegue chamar uma API em **HTTPS** (o navegador bloqueia
  HTTP). Os dois serviços já entregam HTTPS, o que resolve o risco R9 de
  [`seguranca.md`](seguranca.md).

Troque `SEUUSUARIO` pelo seu usuário do PythonAnywhere em todos os comandos.

---

## Parte 1 — API no PythonAnywhere

### 1. Conta

Crie uma conta **Beginner** (gratuita) em <https://www.pythonanywhere.com>.
O usuário escolhido vira o endereço: `SEUUSUARIO.pythonanywhere.com`.

### 2. Código e ambiente virtual

No painel do PythonAnywhere, abra **Consoles → Bash** e rode:

```bash
git clone https://github.com/MiguelSantos1910/ProjetoIntegrador_Backend.git
cd ProjetoIntegrador_Backend

mkvirtualenv --python=/usr/bin/python3.11 easyasset
pip install -r requirements.txt
```

> Se o console fechar, volte ao ambiente com `workon easyasset`.

### 3. Arquivo `.env`

```bash
cp .env.producao.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
nano .env
```

No `nano`, cole a chave gerada em `SECRET_KEY` e troque `SEUUSUARIO`. O
endereço do painel (`CORS_ALLOWED_ORIGINS`) pode ficar com o exemplo por
enquanto; ele é ajustado na Parte 2. Salve com `Ctrl+O`, `Enter` e saia com
`Ctrl+X`.

### 4. Banco, arquivos estáticos e administrador

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py seed_ativos      # opcional: 16 ativos fictícios de demonstração
```

> **Levar o banco atual em vez de começar do zero:** na aba **Files**, envie o
> `db.sqlite3` para `/home/SEUUSUARIO/ProjetoIntegrador_Backend/` e rode
> `python manage.py migrate` de novo. O arquivo contém hashes de senha: apague
> qualquer cópia que ficar fora do servidor.

### 5. Aplicação web

Na aba **Web**:

1. **Add a new web app** → **Next** → **Manual configuration** (não escolha
   "Django") → **Python 3.11**.
2. Em **Code**:
   - *Source code*: `/home/SEUUSUARIO/ProjetoIntegrador_Backend`
   - *Working directory*: `/home/SEUUSUARIO/ProjetoIntegrador_Backend`
3. Em **Virtualenv**: `/home/SEUUSUARIO/.virtualenvs/easyasset`
4. Clique no **WSGI configuration file** (`/var/www/SEUUSUARIO_pythonanywhere_com_wsgi.py`),
   apague todo o conteúdo e cole:

   ```python
   import os
   import sys

   path = "/home/SEUUSUARIO/ProjetoIntegrador_Backend"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

   from django.core.wsgi import get_wsgi_application

   application = get_wsgi_application()
   ```

   Salve. O `.env` é lido pelo próprio `settings.py`, então não é preciso
   repetir as variáveis aqui.
5. Em **Static files**, adicione:
   - URL: `/static/`
   - Directory: `/home/SEUUSUARIO/ProjetoIntegrador_Backend/staticfiles`
6. Em **Security**, ligue **Force HTTPS**.
7. Clique em **Reload** (botão verde no topo).

### 6. Conferir

- `https://SEUUSUARIO.pythonanywhere.com/api/health/` deve responder `200`.
- `https://SEUUSUARIO.pythonanywhere.com/admin/` deve abrir o login do Django
  com o visual normal (se vier sem estilo, revise o passo 5.5).
- No console Bash: `python manage.py check --deploy` (avisos de HSTS são
  esperados; ver "Limitações").

Se algo der erro 500, veja o **Error log** na aba **Web**.

### 7. Backup automático (opcional)

Na aba **Tasks**, crie uma tarefa diária (o plano gratuito permite uma):

```bash
cd /home/SEUUSUARIO/ProjetoIntegrador_Backend && /home/SEUUSUARIO/.virtualenvs/easyasset/bin/python manage.py backup_banco
```

Os arquivos ficam em `backups_banco/` e aparecem na tela de Backup do painel.
Detalhes em [`backup.md`](backup.md).

### 8. Atualizar a API depois de um merge no `main`

```bash
cd ~/ProjetoIntegrador_Backend
workon easyasset
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Depois, **Reload** na aba **Web**. Antes de migrações grandes, gere um backup
pelo painel ou com `python manage.py backup_banco`.

---

## Parte 2 — Painel na Vercel

### 1. Importar o repositório

1. Entre em <https://vercel.com> com a conta do GitHub.
2. **Add New → Project** → importe `ProjetoIntegrador_Frontend`.
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (detectado sozinho)
   - **Build Command**: `npm run build` · **Output Directory**: `dist`
4. Em **Environment Variables**, adicione:
   - `VITE_APP_API_URL` = `https://SEUUSUARIO.pythonanywhere.com/api`
5. **Deploy**.

O arquivo `frontend/vercel.json` faz todas as rotas (`/ativos`,
`/relatorios`...) abrirem o `index.html`; sem ele, recarregar a página daria
404. A cada push no `main`, a Vercel publica de novo sozinha.

> A variável é lida **no build**: depois de mudá-la, use **Redeploy**.

### 2. Liberar o painel na API

Copie o endereço de produção que a Vercel mostrar (ex.:
`https://easy-asset.vercel.app`) e, no PythonAnywhere:

```bash
nano ~/ProjetoIntegrador_Backend/.env
# CORS_ALLOWED_ORIGINS=https://easy-asset.vercel.app
```

Salve e clique em **Reload** na aba **Web**. Sem isso, o login no painel
falha com erro de CORS (aparece no console do navegador, F12).

> Os endereços de *preview* da Vercel (um por branch) são diferentes; só o de
> produção fica liberado.

### Alternativa: Netlify

Também funciona: *Base directory* `frontend`, *Build command* `npm run build`,
*Publish directory* `frontend/dist` e a mesma variável `VITE_APP_API_URL`. O
arquivo `frontend/public/_redirects` já cuida das rotas.

---

## Parte 3 — App Flutter

Gere o APK apontando para a API publicada:

```bash
flutter build apk --dart-define=API_URL=https://SEUUSUARIO.pythonanywhere.com/api
```

Com a API em HTTPS, o `usesCleartextTraffic` do `AndroidManifest.xml` só é
necessário para testar com o back local em HTTP.

---

## Limitações do plano gratuito

- **Validade:** o PythonAnywhere desliga a aplicação web depois de 3 meses sem
  renovação. Na aba **Web**, clique em **Run until 3 months from today** antes
  da apresentação.
- **Processamento:** há uma cota diária de CPU; suficiente para demonstração.
- **Um único site** por conta gratuita.
- **HSTS** (`SECURE_HSTS_SECONDS`) fica desligado por padrão para não prender o
  navegador ao HTTPS durante os testes; ative depois que tudo estiver estável.
- **Usuários de teste:** crie-os no servidor (Django Admin ou cadastro + troca
  de papel pelo professor); as senhas não ficam no repositório.

## Checklist rápido

- [ ] `/api/health/` responde 200 em HTTPS
- [ ] `/admin/` abre com estilo e aceita login
- [ ] `.env` com `DEBUG=False`, `SECRET_KEY` nova e `ALLOWED_HOSTS` certo
- [ ] Painel na Vercel faz login (CORS liberado)
- [ ] Recarregar `/ativos` no painel não dá 404
- [ ] APK gerado com a URL HTTPS
- [ ] Tarefa diária de backup criada
- [ ] Aplicação renovada por 3 meses antes da apresentação
