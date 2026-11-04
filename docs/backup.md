# Backup e restauração do banco

Procedimento de cópia e restauração do banco SQLite do Easy Asset (item
"backup/restauração" da entrega E4 do plano de ensino).

## Como funciona

- O backup usa a API de backup do próprio SQLite (`sqlite3.Connection.backup`),
  que gera uma cópia consistente mesmo com o servidor em uso. Um `cp` do arquivo
  pode copiar uma gravação pela metade.
- Toda cópia passa por `PRAGMA integrity_check` antes de ser aceita.
- Os arquivos ficam em `BACKUP_DIR` (padrão: `backups_banco/`), com permissão
  `600`, e **não são versionados** (estão no `.gitignore`): contêm hashes de senha.
- São mantidos os `BACKUP_MAX` backups mais recentes de cada tipo (padrão: 10).
- Antes de qualquer restauração, o estado atual é salvo como
  `pre_restauracao_AAAAMMDD_HHMMSS.sqlite3`. Assim a restauração também pode
  ser desfeita.
- Só podem ser restaurados ou baixados arquivos gerados pelo próprio sistema
  (nome no formato `db_AAAAMMDD_HHMMSS.sqlite3` ou `pre_restauracao_...`).
  Não há upload.
- Gerar, restaurar, baixar e falhas ficam no log de auditoria: `BACKUP_CRIADO`,
  `BACKUP_RESTAURADO`, `BACKUP_BAIXADO` e `BACKUP_FALHA`.

> **Atenção:** restaurar volta **o banco inteiro** à data do backup, inclusive
> usuários, senhas e logs de auditoria. O que foi registrado depois do backup
> deixa de aparecer (continua no arquivo `pre_restauracao_...`). O evento
> `BACKUP_RESTAURADO` é gravado depois da restauração, então ele permanece.

## Pelo painel web (professor)

Menu **Backup**: "Gerar backup agora" e, em cada linha da lista, "Baixar" e
"Restaurar".
Depois de restaurar, o painel encerra a sessão, porque usuários e tokens podem
ter mudado.

API usada pelo painel (somente `PROFESSOR` ou superusuário; os demais recebem `403`):

| Método | Endpoint | Função |
|---|---|---|
| `GET` | `/api/backups/` | Lista os backups (nome, data, tamanho, quantidade de ativos, usuários e ordens) |
| `POST` | `/api/backups/` | Gera um backup agora |
| `POST` | `/api/backups/<nome>/restaurar/` | Restaura; exige o corpo `{"confirmacao": "RESTAURAR"}` |
| `GET` | `/api/backups/<nome>/download/` | Baixa o arquivo `.sqlite3` (grava `BACKUP_BAIXADO`) |

### Download

O arquivo baixado é uma cópia completa do banco e **contém os hashes de senha
de todos os usuários**. Por isso: só o professor baixa, cada download fica na
auditoria e a resposta vai com `Cache-Control: no-store`. Guarde a cópia num
local privado (é a "cópia fora do servidor" recomendada abaixo), nunca no Git
nem em pastas compartilhadas, e apague as cópias antigas. O arquivo abre em
qualquer leitor de SQLite (por exemplo, DB Browser for SQLite).

## Pelo terminal

```bash
# Gerar um backup
python manage.py backup_banco

# Listar os backups disponíveis
python manage.py restaurar_banco

# Restaurar (pede para digitar RESTAURAR; --sim pula a confirmação)
python manage.py restaurar_banco db_20261104_140000.sqlite3
```

## Agendamento no servidor (cron)

Backup diário às 2h, com log:

```cron
0 2 * * * cd /caminho/do/backend && venv/bin/python manage.py backup_banco >> backups_banco/backup.log 2>&1
```

Recomendado: copiar periodicamente a pasta `backups_banco/` para fora do servidor
(por exemplo, um bucket privado), para o backup não se perder junto com a máquina.

## Evidência (testes)

Testes automatizados em `backups/tests.py`:

```bash
python manage.py test backups
```

Cobrem: acesso sem login (`401`), aluno e suporte (`403`), geração e listagem pelo
professor, download pelo professor (com log) e bloqueado para os demais,
limite de backups mantidos, confirmação obrigatória, nome inválido ou
inexistente, restauração que devolve o banco ao estado do backup e restauração
desfeita pelo backup `pre_restauracao`.

### Roteiro manual com prints

1. Entrar como professor e gerar um backup na tela **Backup** (print da lista).
2. Cadastrar o ativo "TESTE BACKUP" e alterar a descrição de outro ativo (print).
3. Restaurar o backup do passo 1 (print da confirmação e da mensagem de sucesso).
4. Entrar de novo e mostrar que "TESTE BACKUP" não existe e que a descrição voltou
   ao valor anterior (print).
5. Mostrar o evento `BACKUP_RESTAURADO` na aba **Auditoria** (print).
