"""Gera o site da Cloudflare a partir do app Flask: a página e as fixtures de paridade.

- cloudflare/public/index.html: a mesma página do Flask, renderizada com o modelo clef-flash.
- cloudflare/test/fixtures/paridade.json: saídas do Python (requisição, decisões, leitura de respostas)
  que os testes em JavaScript comparam com o porte, para as duas versões nunca divergirem.
"""
import json
import os
from dataclasses import asdict

import decisao
import jev
from app import criar_app

RAIZ = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(RAIZ, "cloudflare")
MODELO = "clef-flash"
MENSAGEM_TESTE = "Mensagem de teste: pague o boleto em http://exemplo.test"


def gravar(caminho, conteudo):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(conteudo)


def gerar_html():
    os.environ.pop("JEV_MOCK", None)
    os.environ["JEV_MODEL"] = MODELO
    html = criar_app().test_client().get("/").get_data(as_text=True)
    assert "SIMULADO" not in html and MODELO in html
    gravar(os.path.join(SITE, "public", "index.html"), html)


def casos_decisao():
    casos = []
    for tipo in jev.TIPOS_GOLPE:
        for risco in range(1, 6):
            for pede in (0.0, 0.3, 0.49, 0.5, 0.9):
                for conf in (None, 0.3, 0.49, 0.5, 0.55, 0.9):
                    analise = jev.Analise(tipo=tipo, pede_dados=pede, risco=risco, confianca=conf)
                    casos.append({"entrada": asdict(analise), "esperado": asdict(decisao.decidir(analise))})
    return casos


def casos_resposta():
    sinteticos = {
        "com_campo_type_e_probabilidades": {"answers": {
            "tipo_golpe": {"type": "choice", "choice": "premio_falso", "probabilities": {"premio_falso": 0.7}},
            "pede_dados": {"type": "noul", "noul": 0.1},
            "risco": {"type": "score", "score": 0.0, "confidence": 0.4}}},
        "score_negativo": {"answers": {"tipo_golpe": {"choice": "mensagem_legitima"}, "pede_dados": {"noul": 0.0}, "risco": {"score": -0.3}}},
        "score_acima_do_maximo": {"answers": {"tipo_golpe": {"choice": "boleto_falso", "confidence": 0.9}, "pede_dados": {"noul": 1}, "risco": {"score": 4.9}}},
        "score_meio": {"answers": {"tipo_golpe": {"choice": "boleto_falso"}, "pede_dados": {"noul": 0.5}, "risco": {"score": 2.5}}},
    }
    invalidos = {
        "vazio": {},
        "answers_lista": {"answers": []},
        "faltam_perguntas": {"answers": {"tipo_golpe": {"choice": "boleto_falso"}}},
        "tipo_desconhecido": {"answers": {"tipo_golpe": {"choice": "inventado"}, "pede_dados": {"noul": 0.1}, "risco": {"score": 1}}},
        "choice_lista": {"answers": {"tipo_golpe": {"choice": ["x"]}, "pede_dados": {"noul": 0.1}, "risco": {"score": 1}}},
        "noul_fora_do_intervalo": {"answers": {"tipo_golpe": {"choice": "boleto_falso"}, "pede_dados": {"noul": 1.5}, "risco": {"score": 1}}},
        "noul_texto": {"answers": {"tipo_golpe": {"choice": "boleto_falso"}, "pede_dados": {"noul": "alto"}, "risco": {"score": 1}}},
        "type_errado": {"answers": {"tipo_golpe": {"type": "score", "choice": "boleto_falso"}, "pede_dados": {"noul": 0.1}, "risco": {"score": 1}}},
    }
    casos = []
    bruto = os.path.join(RAIZ, "prints", "bruto.json")
    if os.path.exists(bruto):  # respostas reais do Clef guardadas por rodar_exemplos.py
        with open(bruto, encoding="utf-8") as f:
            for nome, dados in json.load(f).items():
                sinteticos[f"clef_real_{nome}"] = dados
    for nome, dados in sinteticos.items():
        casos.append({"nome": nome, "dados": dados, "esperado": asdict(jev.parse_resposta(dados))})
    for nome, dados in invalidos.items():
        try:
            jev.parse_resposta(dados)
        except jev.JevRespostaErro:
            casos.append({"nome": nome, "dados": dados, "esperado": {"erro": True}})
        else:
            raise SystemExit(f"o caso inválido '{nome}' foi aceito pelo Python")
    return casos


def gerar_fixtures():
    fixtures = {
        "requisicao": {"mensagem": MENSAGEM_TESTE, "modelo": MODELO, "esperado": jev.montar_requisicao(MENSAGEM_TESTE, MODELO)},
        "rotulos": decisao.ROTULOS,
        "decisao": casos_decisao(),
        "resposta": casos_resposta(),
    }
    gravar(os.path.join(SITE, "test", "fixtures", "paridade.json"), json.dumps(fixtures, ensure_ascii=False, indent=1))
    return fixtures


if __name__ == "__main__":
    gerar_html()
    f = gerar_fixtures()
    print(f"index.html gerado; fixtures: {len(f['decisao'])} decisões, {len(f['resposta'])} respostas")
