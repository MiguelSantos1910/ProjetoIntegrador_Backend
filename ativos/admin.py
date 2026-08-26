from django.contrib import admin

from .models import Ativo, HistoricoMovimentacao


class HistoricoInline(admin.TabularInline):
    model = HistoricoMovimentacao
    extra = 0
    readonly_fields = ["data"]


@admin.register(Ativo)
class AtivoAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "numero_patrimonio", "status", "sala", "codigo_qr"]
    list_filter = ["tipo", "status", "sala"]
    search_fields = ["descricao", "numero_patrimonio", "codigo_qr"]
    readonly_fields = ["codigo_qr", "data_cadastro", "atualizado_em"]
    inlines = [HistoricoInline]


@admin.register(HistoricoMovimentacao)
class HistoricoMovimentacaoAdmin(admin.ModelAdmin):
    list_display = ["ativo", "tipo_evento", "usuario", "data"]
    list_filter = ["tipo_evento"]
