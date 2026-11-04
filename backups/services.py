"""
Backup e restauração do banco SQLite.

Usa a API de backup do próprio SQLite (sqlite3.Connection.backup), que copia
o banco de forma consistente mesmo com o servidor em uso — ao contrário de um
simples "cp" do arquivo, que pode pegar uma gravação pela metade.

Usado pela API (backups/views.py) e pelos comandos de terminal
(backup_banco e restaurar_banco), para que os dois sigam as mesmas regras.
"""

import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone


# Só arquivos gerados pelo próprio sistema podem ser listados ou restaurados.
# O formato fixo também impede nomes como "../../outro_arquivo".
PADRAO_NOME = re.compile(
    r"^(?P<tipo>db|pre_restauracao)_(?P<data>\d{8}_\d{6})(?:_(?P<seq>\d+))?\.sqlite3$"
)

# Tabelas contadas para conferir o conteúdo de cada backup.
TABELAS_CONTAGEM = {
    "ativos": "ativos_ativo",
    "usuarios": "auth_user",
    "ordens": "ordens_manutencao_ordemmanutencao",
}


class BackupErro(Exception):
    """Falha esperada de backup/restauração, com o status HTTP sugerido."""

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


class BackupNaoEncontrado(BackupErro):
    def __init__(self, nome):
        super().__init__(f"Backup '{nome}' não encontrado.", status=404)


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------------

def _diretorio():
    diretorio = Path(settings.BACKUP_DIR)
    diretorio.mkdir(parents=True, exist_ok=True)

    try:
        # Backups têm hashes de senha: só o usuário do servidor acessa.
        os.chmod(diretorio, 0o700)
    except OSError:
        pass

    return diretorio


def _exigir_sqlite():
    if connection.vendor != "sqlite":
        raise BackupErro(
            "O backup pelo sistema está disponível apenas para SQLite.",
            status=501,
        )


def _conexao_sqlite():
    """Conexão sqlite3 que o Django está usando."""

    connection.ensure_connection()
    return connection.connection


def _abrir_somente_leitura(caminho):
    return sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)


def _contagens(conexao):
    contagens = {}

    for chave, tabela in TABELAS_CONTAGEM.items():
        try:
            contagens[chave] = conexao.execute(
                f'SELECT COUNT(*) FROM "{tabela}"'
            ).fetchone()[0]
        except sqlite3.DatabaseError:
            contagens[chave] = None

    return contagens


def _verificar_arquivo(caminho):
    """
    Confere a integridade de um arquivo de backup.
    Retorna as contagens ou lança BackupErro se o arquivo estiver corrompido.
    """

    try:
        with closing(_abrir_somente_leitura(caminho)) as conexao:
            resultado = conexao.execute("PRAGMA integrity_check").fetchone()[0]

            if resultado != "ok":
                raise BackupErro(
                    f"O arquivo '{caminho.name}' está corrompido ({resultado})."
                )

            return _contagens(conexao)
    except sqlite3.DatabaseError as erro:
        raise BackupErro(
            f"O arquivo '{caminho.name}' não é um banco SQLite válido ({erro})."
        ) from erro


def _novo_caminho(tipo):
    diretorio = _diretorio()
    carimbo = timezone.localtime().strftime("%Y%m%d_%H%M%S")

    # Vários backups no mesmo segundo recebem _1, _2... A sequência continua
    # da maior existente (e não do primeiro nome livre), para que um nome
    # liberado pela limpeza não faça um backup novo parecer o mais antigo.
    sequencias = [
        int(m["seq"] or 0)
        for caminho in diretorio.iterdir()
        if (m := PADRAO_NOME.match(caminho.name))
        and m["tipo"] == tipo
        and m["data"] == carimbo
    ]

    if not sequencias:
        return diretorio / f"{tipo}_{carimbo}.sqlite3"

    return diretorio / f"{tipo}_{carimbo}_{max(sequencias) + 1}.sqlite3"


def _info(caminho, contagens=None):
    correspondencia = PADRAO_NOME.match(caminho.name)

    criado_em = timezone.make_aware(
        datetime.strptime(correspondencia["data"], "%Y%m%d_%H%M%S")
    )

    return {
        "nome": caminho.name,
        "tipo": correspondencia["tipo"],
        "criado_em": criado_em.isoformat(),
        "tamanho_bytes": caminho.stat().st_size,
        "contagens": contagens,
    }


def _ordem(nome):
    """Chave de ordenação cronológica: data e, no mesmo segundo, a sequência."""

    correspondencia = PADRAO_NOME.match(nome)
    return (correspondencia["data"], int(correspondencia["seq"] or 0))


def _remover_antigos(tipo, manter):
    """Mantém apenas os BACKUP_MAX backups mais recentes de cada tipo."""

    maximo = max(int(settings.BACKUP_MAX), 1)

    arquivos = sorted(
        (
            caminho
            for caminho in _diretorio().iterdir()
            if (m := PADRAO_NOME.match(caminho.name)) and m["tipo"] == tipo
        ),
        key=lambda caminho: _ordem(caminho.name),
        reverse=True,
    )

    for caminho in arquivos[maximo:]:
        if caminho != manter:
            caminho.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# OPERAÇÕES
# ---------------------------------------------------------------------------

def criar_backup(tipo="db"):
    """Copia o banco atual para um novo arquivo em BACKUP_DIR."""

    _exigir_sqlite()

    destino = _novo_caminho(tipo)

    try:
        with closing(sqlite3.connect(destino)) as conexao_destino:
            _conexao_sqlite().backup(conexao_destino)

        os.chmod(destino, 0o600)
        contagens = _verificar_arquivo(destino)
    except Exception:
        destino.unlink(missing_ok=True)
        raise

    info = _info(destino, contagens)
    _remover_antigos(tipo, manter=destino)

    return info


def listar_backups():
    """Backups disponíveis, do mais recente para o mais antigo."""

    _exigir_sqlite()

    backups = []

    for caminho in _diretorio().iterdir():
        if not PADRAO_NOME.match(caminho.name):
            continue

        try:
            contagens = _verificar_arquivo(caminho)
        except BackupErro:
            contagens = None

        backups.append(_info(caminho, contagens))

    return sorted(
        backups,
        key=lambda b: (_ordem(b["nome"]), b["tipo"] == "db"),
        reverse=True,
    )


def caminho_backup(nome):
    """Valida o nome recebido e devolve o caminho do arquivo."""

    if not PADRAO_NOME.match(nome or ""):
        raise BackupErro("Nome de backup inválido.")

    diretorio = _diretorio().resolve()
    caminho = (diretorio / nome).resolve()

    if caminho.parent != diretorio:
        raise BackupErro("Nome de backup inválido.")

    if not caminho.is_file():
        raise BackupNaoEncontrado(nome)

    return caminho


def restaurar_backup(nome):
    """
    Substitui o conteúdo do banco atual pelo do backup escolhido.

    Antes de restaurar, grava um backup "pre_restauracao" do estado atual,
    para que a restauração também possa ser desfeita.
    """

    _exigir_sqlite()

    caminho = caminho_backup(nome)
    contagens = _verificar_arquivo(caminho)

    if connection.in_atomic_block:
        raise BackupErro(
            "A restauração não pode rodar dentro de uma transação.",
            status=500,
        )

    seguranca = criar_backup(tipo="pre_restauracao")

    with closing(_abrir_somente_leitura(caminho)) as origem:
        origem.backup(_conexao_sqlite())

    return {
        "restaurado": _info(caminho, contagens),
        "backup_seguranca": seguranca,
    }
