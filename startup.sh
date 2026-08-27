#!/bin/bash
# Comando de inicialização do backend na Azure App Service.
# Cole exatamente isto no campo "Comando de inicialização" (Startup Command)
# das Configurações Gerais do App Service, OU aponte o Startup Command para
# este arquivo (veja o README, seção "Deploy na Azure").
gunicorn --bind=0.0.0.0:8000 --timeout 600 config.wsgi
