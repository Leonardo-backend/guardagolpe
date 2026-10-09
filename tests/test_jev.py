import os
import re
from unittest import mock

import pytest
import requests

import jev

RESPOSTA_OK = {
    "model": "jev-teste",
    "answers": {
        "tipo_golpe": {"choice": "boleto_falso", "probabilities": {"boleto_falso": 0.92}, "confidence": 0.88},
        "pede_dados": {"noul": 0.87},
        "risco": {"score": 3.8, "probabilities": [0.0, 0.0, 0.1, 0.2, 0.7], "confidence": 0.79},
    },
}


def test_requisicao_tem_as_tres_perguntas_com_os_tipos_certos():
    corpo = jev.montar_requisicao("Oi, tudo bem?", "jev-teste")
    assert corpo["model"] == "jev-teste"
    assert corpo["state"] == "Oi, tudo bem?"
    q = corpo["questions"]
    assert set(q) == {"tipo_golpe", "pede_dados", "risco"}
    assert q["tipo_golpe"]["type"] == "choice"
    assert q["pede_dados"]["type"] == "noul"
    assert q["risco"]["type"] == "score"


def test_requisicao_respeita_os_limites_do_jev():
    q = jev.montar_requisicao("x")["questions"]
    ids = q["tipo_golpe"]["criteria"]
    assert 2 <= len(ids) <= 8
    assert all(re.fullmatch(r"[a-z][a-z0-9_]{0,29}", i) for i in ids)
    assert set(q["pede_dados"]["criteria"]) == {"true", "false"}
    assert len(q["risco"]["criteria"]) == 5
    for pergunta in q.values():
        assert len(pergunta["instructions"]) <= 500
    textos = list(ids.values()) + list(q["pede_dados"]["criteria"].values()) + q["risco"]["criteria"]
    assert all(len(t) <= 250 for t in textos)


def test_parse_resposta_ok():
    a = jev.parse_resposta(RESPOSTA_OK)
    assert a == jev.Analise(tipo="boleto_falso", pede_dados=0.87, risco=5, confianca=0.88, confianca_risco=0.79)


def test_parse_aceita_variante_com_campo_type():
    dados = {
        "answers": {
            "tipo_golpe": {"type": "choice", "choice": "premio_falso"},
            "pede_dados": {"type": "noul", "noul": 0.1},
            "risco": {"type": "score", "score": 0.0},
        }
    }
    a = jev.parse_resposta(dados)
    assert (a.tipo, a.pede_dados, a.risco, a.confianca) == ("premio_falso", 0.1, 1, None)


@pytest.mark.parametrize("score,esperado", [(0, 1), (0.4, 1), (1.2, 2), (2.5, 4), (4, 5), (4.9, 5), (-0.3, 1)])
def test_score_vira_nivel_de_1_a_5(score, esperado):
    dados = {
        "answers": {
            "tipo_golpe": {"choice": "mensagem_legitima"},
            "pede_dados": {"noul": 0.0},
            "risco": {"score": score},
        }
    }
    assert jev.parse_resposta(dados).risco == esperado


def test_confianca_e_a_do_choice_e_a_do_score_fica_separada():
    # No teste real (Clef) a confiança do Score ficou em 26%-37% mesmo nas respostas certas,
    # então ela não pode alimentar a regra de incerteza; a do Choice é guardada à parte.
    dados = {
        "answers": {
            "tipo_golpe": {"choice": "boleto_falso", "confidence": 0.9},
            "pede_dados": {"noul": 0.5},
            "risco": {"score": 3, "confidence": 0.3},
        }
    }
    a = jev.parse_resposta(dados)
    assert a.confianca == 0.9
    assert a.confianca_risco == 0.3


def test_confianca_do_choice_cai_para_a_probabilidade_da_opcao_escolhida():
    dados = {
        "answers": {
            "tipo_golpe": {"choice": "boleto_falso", "probabilities": {"boleto_falso": 0.7, "premio_falso": 0.3}},
            "pede_dados": {"noul": 0.5},
            "risco": {"score": 3},
        }
    }
    a = jev.parse_resposta(dados)
    assert a.confianca == 0.7
    assert a.confianca_risco is None


@pytest.mark.parametrize(
    "dados",
    [
        {},
        {"answers": []},
        {"answers": {"tipo_golpe": {"choice": "boleto_falso"}}},
        {"answers": {"tipo_golpe": {"choice": "inventado"}, "pede_dados": {"noul": 0.1}, "risco": {"score": 1}}},
        {"answers": {"tipo_golpe": {"choice": ["x"]}, "pede_dados": {"noul": 0.1}, "risco": {"score": 1}}},
        {"answers": {"tipo_golpe": {"choice": "boleto_falso"}, "pede_dados": {"noul": 1.5}, "risco": {"score": 1}}},
        {"answers": {"tipo_golpe": {"choice": "boleto_falso"}, "pede_dados": {"noul": "alto"}, "risco": {"score": 1}}},
        {"answers": {"tipo_golpe": {"type": "score", "choice": "boleto_falso"}, "pede_dados": {"noul": 0.1}, "risco": {"score": 1}}},
    ],
)
def test_parse_rejeita_resposta_fora_do_formato(dados):
    with pytest.raises(jev.JevRespostaErro):
        jev.parse_resposta(dados)


class RespostaFalsa:
    def __init__(self, status=200, corpo=None, json_invalido=False):
        self.status_code = status
        self._corpo = corpo
        self._json_invalido = json_invalido

    def json(self):
        if self._json_invalido:
            raise ValueError("sem json")
        return self._corpo


class HttpFalso:
    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta
        self.erro = erro
        self.chamadas = []

    def post(self, url, json, headers, timeout):
        self.chamadas.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if self.erro:
            raise self.erro
        return self.resposta


@pytest.fixture(autouse=True)
def limpar_ambiente(monkeypatch):
    for nome in ("JEV_MOCK", "JEV_API_KEY", "JEV_BASE_URL", "JEV_MODEL"):
        monkeypatch.delenv(nome, raising=False)


def test_chamada_envia_chave_url_modelo_e_timeout():
    http = HttpFalso(RespostaFalsa(200, RESPOSTA_OK))
    bruto = jev.chamar_api("  oi  ", chave="segredo", base_url="https://x.test/v1", modelo="jev-x", http=http)
    assert bruto == RESPOSTA_OK
    c = http.chamadas[0]
    assert c["url"] == "https://x.test/v1"
    assert c["headers"]["Authorization"] == "Bearer segredo"
    assert c["json"]["model"] == "jev-x"
    assert c["json"]["state"] == "oi"
    assert c["timeout"] == jev.TIMEOUT_SEGUNDOS


def test_chamada_usa_variaveis_de_ambiente(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "da-env")
    monkeypatch.setenv("JEV_BASE_URL", "https://env.test/api")
    monkeypatch.setenv("JEV_MODEL", "jev-env")
    http = HttpFalso(RespostaFalsa(200, RESPOSTA_OK))
    jev.chamar_api("oi", http=http)
    c = http.chamadas[0]
    assert (c["url"], c["json"]["model"]) == ("https://env.test/api", "jev-env")
    assert c["headers"]["Authorization"] == "Bearer da-env"


def test_sem_chave_levanta_erro_de_configuracao():
    with pytest.raises(jev.JevConfigErro):
        jev.chamar_api("oi", http=HttpFalso(RespostaFalsa(200, RESPOSTA_OK)))


@pytest.mark.parametrize("texto", ["", "   ", None, "a" * 4001])
def test_mensagem_invalida(texto):
    with pytest.raises(jev.MensagemInvalida):
        jev.chamar_api(texto, chave="k", http=HttpFalso(RespostaFalsa(200, RESPOSTA_OK)))


@pytest.mark.parametrize(
    "status,trecho",
    [(401, "chave"), (403, "chave"), (402, "crédito"), (429, "Limite"), (500, "instável"), (418, "418")],
)
def test_status_http_vira_mensagem_clara(status, trecho):
    http = HttpFalso(RespostaFalsa(status, {}))
    with pytest.raises(jev.JevErro) as e:
        jev.chamar_api("oi", chave="segredo", http=http)
    assert trecho in str(e.value)
    assert "segredo" not in str(e.value)


def test_403_mostra_o_motivo_dado_pelo_servidor():
    corpo = {"error": {"message": "Free tier users do not have access to this model.", "type": "no_providers_available"}}
    with pytest.raises(jev.JevErro) as e:
        jev.chamar_api("oi", chave="segredo", http=HttpFalso(RespostaFalsa(403, corpo)))
    assert "Free tier users do not have access" in str(e.value)
    assert "segredo" not in str(e.value)


def test_resposta_da_cloudflare_vem_embrulhada_em_result():
    embrulhada = {"result": RESPOSTA_OK, "success": True, "errors": [], "messages": []}
    http = HttpFalso(RespostaFalsa(200, embrulhada))
    assert jev.chamar_api("oi", chave="k", http=http) == RESPOSTA_OK
    assert jev.consultar("oi", chave="k", http=http).tipo == "boleto_falso"


def test_erro_da_cloudflare_mostra_a_mensagem_de_errors():
    corpo = {"result": None, "success": False, "errors": [{"code": 10000, "message": "Authentication error"}]}
    with pytest.raises(jev.JevErro, match="Authentication error"):
        jev.chamar_api("oi", chave="k", http=HttpFalso(RespostaFalsa(403, corpo)))
    # 200 com success=false também é erro
    with pytest.raises(jev.JevErro, match="Authentication error"):
        jev.chamar_api("oi", chave="k", http=HttpFalso(RespostaFalsa(200, corpo)))


def test_timeout_e_falha_de_rede():
    with pytest.raises(jev.JevErro, match="demorou"):
        jev.chamar_api("oi", chave="k", http=HttpFalso(erro=requests.Timeout()))
    with pytest.raises(jev.JevErro, match="rede"):
        jev.chamar_api("oi", chave="k", http=HttpFalso(erro=requests.ConnectionError()))


def test_resposta_que_nao_e_json():
    with pytest.raises(jev.JevRespostaErro):
        jev.chamar_api("oi", chave="k", http=HttpFalso(RespostaFalsa(200, json_invalido=True)))


def test_consultar_devolve_analise_nao_simulada():
    http = HttpFalso(RespostaFalsa(200, RESPOSTA_OK))
    a = jev.consultar("oi", chave="k", http=http)
    assert a.tipo == "boleto_falso" and a.risco == 5 and a.simulado is False


def test_modo_simulado_nao_chama_a_rede_e_marca_simulado(monkeypatch):
    monkeypatch.setenv("JEV_MOCK", "1")
    http = HttpFalso(RespostaFalsa(200, RESPOSTA_OK))
    a = jev.consultar("Seu boleto venceu, pague no link", http=http)
    assert http.chamadas == []
    assert a.simulado is True and a.tipo == "boleto_falso" and a.risco == 5


def test_modo_simulado_reconhece_mensagem_legitima(monkeypatch):
    monkeypatch.setenv("JEV_MOCK", "1")
    a = jev.consultar("A aula de sexta foi remarcada para as 19h.")
    assert a.tipo == "mensagem_legitima" and a.risco == 1 and a.pede_dados < 0.5


def test_carregar_env_le_arquivo_sem_sobrescrever(tmp_path):
    arquivo = tmp_path / ".env"
    arquivo.write_text('# comentário\nJEV_API_KEY="abc"\nJEV_MODEL=jev-x\n\nlinha-sem-igual\n', encoding="utf-8")
    # patch.dict restaura o ambiente no fim, mesmo com o setdefault do carregar_env
    with mock.patch.dict(os.environ, {"JEV_MODEL": "ja-definido"}):
        jev.carregar_env(str(arquivo))
        assert os.environ["JEV_API_KEY"] == "abc"
        assert os.environ["JEV_MODEL"] == "ja-definido"
        jev.carregar_env(str(tmp_path / "nao-existe"))  # não deve falhar
    assert "JEV_API_KEY" not in os.environ
