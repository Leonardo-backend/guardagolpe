import importlib
import os
import sys

import jev


def importar_wsgi(monkeypatch, chamadas):
    monkeypatch.setattr(jev, "carregar_env", lambda caminho=".env": chamadas.append(caminho))
    sys.modules.pop("wsgi", None)
    return importlib.import_module("wsgi")


def test_wsgi_carrega_o_env_da_pasta_do_projeto_e_expoe_o_app(monkeypatch):
    chamadas = []
    modulo = importar_wsgi(monkeypatch, chamadas)
    assert len(chamadas) == 1
    assert os.path.basename(chamadas[0]) == ".env"
    assert os.path.isabs(chamadas[0]), "o caminho não pode depender da pasta de onde o gunicorn foi chamado"
    assert os.path.dirname(chamadas[0]) == os.path.dirname(os.path.abspath(modulo.__file__))
    assert modulo.application.test_client().get("/").status_code == 200
    sys.modules.pop("wsgi", None)


def test_wsgi_nao_sobrescreve_variaveis_ja_definidas_no_ambiente(tmp_path, monkeypatch):
    # carregar_env usa setdefault: o que já está no ambiente do servidor vence o .env
    arquivo = tmp_path / ".env"
    arquivo.write_text("JEV_MODEL=do-arquivo\n", encoding="utf-8")
    monkeypatch.setenv("JEV_MODEL", "do-ambiente")
    jev.carregar_env(str(arquivo))
    assert os.environ["JEV_MODEL"] == "do-ambiente"
