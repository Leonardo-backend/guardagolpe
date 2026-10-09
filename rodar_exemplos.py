"""Consulta o JEV de verdade com os 3 exemplos e salva prints/resultados.json (nunca a chave)."""
import json
import os
import sys
from datetime import date
from urllib.parse import urlparse

import decisao
import jev
from exemplos import EXEMPLOS

PASTA = os.path.dirname(os.path.abspath(__file__))
PRINTS = os.path.join(PASTA, "prints")


def salvar(nome, dados):
    os.makedirs(PRINTS, exist_ok=True)
    with open(os.path.join(PRINTS, nome), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def main():
    jev.carregar_env(os.path.join(PASTA, ".env"))
    if jev.modo_simulado():
        sys.exit("JEV_MOCK=1 está ligado. Desligue para fazer o teste real.")

    base_url = os.environ.get("JEV_BASE_URL") or jev.BASE_URL_PADRAO
    modelo = os.environ.get("JEV_MODEL") or jev.MODELO_PADRAO
    brutos, resultados = {}, []
    for ex in EXEMPLOS:
        try:
            bruto = jev.chamar_api(ex["texto"])
            brutos[ex["id"]] = bruto
            analise = jev.parse_resposta(bruto)
        except jev.JevErro as erro:
            salvar("bruto.json", brutos)
            sys.exit(f"Falhou no exemplo '{ex['id']}': {erro}\nResposta bruta (se houve) em prints/bruto.json")
        v = decisao.decidir(analise)
        resultados.append({
            "id": ex["id"], "titulo": ex["titulo"], "esperado": ex["esperado"], "veredito": v.nivel,
            "tipo": analise.tipo, "tipo_rotulo": decisao.ROTULOS[analise.tipo],
            "pede_dados": analise.pede_dados, "risco": analise.risco, "confianca": analise.confianca,
            "confianca_risco": analise.confianca_risco,
        })
        print(f"{ex['titulo']:<20} esperado={ex['esperado']:<7} obtido={v.nivel:<8} "
              f"tipo={analise.tipo} risco={analise.risco} pede={analise.pede_dados:.2f}")

    salvar("bruto.json", brutos)
    salvar("resultados.json", {
        "data": date.today().isoformat(), "provedor": urlparse(base_url).netloc, "modelo": modelo,
        "modelo_respondido": next(iter(brutos.values())).get("model"), "simulado": False, "exemplos": resultados,
    })
    print("Salvo em prints/resultados.json e prints/bruto.json")


if __name__ == "__main__":
    main()
