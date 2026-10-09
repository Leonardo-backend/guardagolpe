"""Servidor Flask do GuardaGolpe."""
import os
from dataclasses import asdict

from flask import Flask, jsonify, render_template, request

import decisao
import jev
from exemplos import EXEMPLOS

PASTA = os.path.dirname(os.path.abspath(__file__))


def criar_app(consultar=jev.consultar):
    app = Flask(__name__)

    @app.get("/")
    def pagina():
        modelo = os.environ.get("JEV_MODEL") or jev.MODELO_PADRAO
        return render_template("index.html", exemplos=EXEMPLOS, simulado=jev.modo_simulado(), modelo=modelo)

    @app.post("/analisar")
    def analisar():
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            dados = {}
        try:
            mensagem = jev.validar_mensagem(dados.get("mensagem"))
            analise = consultar(mensagem)
        except jev.MensagemInvalida as erro:
            return jsonify(erro=str(erro)), 400
        except jev.JevErro as erro:
            return jsonify(erro=str(erro)), erro.status_http
        veredito = decisao.decidir(analise)
        modelo = os.environ.get("JEV_MODEL") or jev.MODELO_PADRAO
        return jsonify(
            analise=asdict(analise),
            veredito=asdict(veredito),
            tipo_rotulo=decisao.ROTULOS[analise.tipo],
            requisicao=jev.montar_requisicao(mensagem, modelo),
        )

    return app


if __name__ == "__main__":
    jev.carregar_env(os.path.join(PASTA, ".env"))
    # Local: 127.0.0.1:5000. Numa máquina na nuvem, defina GUARDAGOLPE_HOST=0.0.0.0 (e a porta, se quiser).
    criar_app().run(
        host=os.environ.get("GUARDAGOLPE_HOST", "127.0.0.1"),
        port=int(os.environ.get("GUARDAGOLPE_PORT", "5000")),
        debug=False,
    )
