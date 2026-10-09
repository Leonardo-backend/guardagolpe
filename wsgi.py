"""Ponto de entrada para servidores WSGI (gunicorn): carrega o .env da pasta do projeto e cria o app.

Uso: gunicorn -b 0.0.0.0:8000 wsgi:application
"""
import os

import jev
from app import criar_app

# Variáveis já definidas no ambiente do servidor têm prioridade sobre as do .env.
jev.carregar_env(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

application = criar_app()
