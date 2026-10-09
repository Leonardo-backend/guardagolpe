import jev
from app import criar_app


def cliente(consultar):
    return criar_app(consultar).test_client()


def consulta_ok(mensagem):
    return jev.Analise("boleto_falso", 0.9, 5, 0.9)


def test_pagina_inicial_mostra_nome_e_exemplos(monkeypatch):
    monkeypatch.delenv("JEV_MOCK", raising=False)
    r = cliente(consulta_ok).get("/")
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "GuardaGolpe" in html and "Boleto falso" in html
    assert "SIMULADO" not in html


def test_pagina_mostra_o_modelo_em_uso(monkeypatch):
    monkeypatch.setenv("JEV_MODEL", "clef-flash")
    assert "clef-flash" in cliente(consulta_ok).get("/").get_data(as_text=True)
    monkeypatch.delenv("JEV_MODEL")
    assert jev.MODELO_PADRAO in cliente(consulta_ok).get("/").get_data(as_text=True)


def test_pagina_avisa_quando_esta_em_modo_simulado(monkeypatch):
    monkeypatch.setenv("JEV_MOCK", "1")
    assert "SIMULADO" in cliente(consulta_ok).get("/").get_data(as_text=True)


def test_analisar_devolve_veredito_e_requisicao_sem_chave(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "segredo-123")
    r = cliente(consulta_ok).post("/analisar", json={"mensagem": "  pague o boleto  "})
    corpo = r.get_json()
    assert r.status_code == 200
    assert corpo["veredito"]["nivel"] == "perigo"
    assert corpo["tipo_rotulo"] == "Boleto falso"
    assert corpo["analise"]["risco"] == 5
    assert corpo["requisicao"]["state"] == "pague o boleto"
    texto = r.get_data(as_text=True)
    assert "segredo-123" not in texto and "Bearer" not in texto


def test_mensagem_vazia_ou_corpo_invalido_da_400():
    c = cliente(consulta_ok)
    assert c.post("/analisar", json={"mensagem": "   "}).status_code == 400
    assert c.post("/analisar", data="isso nao e json", content_type="text/plain").status_code == 400
    assert c.post("/analisar", json=["lista"]).status_code == 400


def test_erro_do_jev_vira_502_com_mensagem():
    def falha(_):
        raise jev.JevErro("O JEV está instável no momento. Tente de novo.")

    r = cliente(falha).post("/analisar", json={"mensagem": "oi"})
    assert r.status_code == 502
    assert "instável" in r.get_json()["erro"]


def test_chave_ausente_vira_503():
    def sem_chave(_):
        raise jev.JevConfigErro("Chave do JEV não configurada.")

    assert cliente(sem_chave).post("/analisar", json={"mensagem": "oi"}).status_code == 503
