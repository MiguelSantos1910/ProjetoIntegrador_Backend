from django.urls import path

from .views import BackupListCreateView, BackupRestaurarView


urlpatterns = [
    path("", BackupListCreateView.as_view(), name="backups"),
    path(
        "<str:nome>/restaurar/",
        BackupRestaurarView.as_view(),
        name="backup-restaurar",
    ),
]
