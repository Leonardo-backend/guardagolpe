"""Cliente do JEV: monta a requisição, chama a API e normaliza a resposta."""
import math
import os
from dataclasses import dataclass, replace

import requests

BASE_URL_PADRAO = "https://api.typesafe.ai/v1/systemone"
MODELO_PADRAO = "jev-latest"
LIMITE_MENSAGEM = 4000
TIMEOUT_SEGUNDOS = 60
SCORE_COMECA_EM_ZERO = True  # confirmar na primeira chamada real (Task 7)

TIPOS_GOLPE = {
    "boleto_falso": "Boleto, fatura ou cobrança falsa, com link ou código de pagamento adulterado",
    "phishing_bancario": "Falso aviso de banco ou cartão pedindo senha, código ou confirmação de dados",
    "falso_suporte": "Falso atendente, suporte técnico ou parente pedindo dinheiro ou acesso ao aparelho",
    "premio_falso": "Prêmio, sorteio, herança ou oferta boa demais para ser verdade",
    "mensagem_legitima": "Mensagem comum, sem sinais de golpe",
}

NIVEIS_RISCO = [
    "Sem risco: mensagem normal, sem pedido suspeito",
    "Risco baixo: algum detalhe estranho, mas sem pedido de dados ou dinheiro",
    "Risco médio: sinais de golpe, como urgência ou link desconhecido",
    "Risco alto: pede dados, dinheiro ou clique, com urgência ou ameaça",
    "Risco crítico: golpe evidente, com link falso e pedido direto de dinheiro ou senha",
]


class JevErro(Exception):
    status_http = 502


class JevConfigErro(JevErro):
    status_http = 503


class JevRespostaErro(JevErro):
    pass


class MensagemInvalida(ValueError):
    pass


@dataclass(frozen=True)
class Analise:
    tipo: str
    pede_dados: float
    risco: int
    confianca: "float | None"  # confiança do Choice (tipo de golpe); alimenta a regra de incerteza
    simulado: bool = False
    confianca_risco: "float | None" = None  # confiança do Score, guardada à parte (escala diferente)


def validar_mensagem(mensagem):
    texto = (mensagem or "").strip()
    if not texto:
        raise MensagemInvalida("Cole uma mensagem para analisar.")
    if len(texto) > LIMITE_MENSAGEM:
        raise MensagemInvalida(f"A mensagem passa de {LIMITE_MENSAGEM} caracteres.")
    return texto


def montar_requisicao(mensagem, modelo=MODELO_PADRAO):
    return {
        "model": modelo,
        "state": mensagem,
        "questions": {
            "tipo_golpe": {
                "type": "choice",
                "instructions": "A mensagem recebida é qual tipo de golpe? Escolha mensagem_legitima se não houver sinais de golpe.",
                "criteria": dict(TIPOS_GOLPE),
            },
            "pede_dados": {
                "type": "noul",
                "instructions": "A mensagem pede dinheiro, senha, código, dados pessoais ou um clique em link, de forma suspeita ou urgente?",
                "criteria": {
                    "true": "Pede dinheiro, senha, código, dados pessoais ou clique em link",
                    "false": "Não pede nada disso",
                },
            },
            "risco": {
                "type": "score",
                "instructions": "Qual o nível de risco de golpe da mensagem recebida?",
                "criteria": list(NIVEIS_RISCO),
            },
        },
    }


def _numero(valor, nome):
    if isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, (int, float)):
        return float(valor)
    raise JevRespostaErro(f"O campo '{nome}' veio em formato inesperado.")


def _resposta(answers, nome, tipo):
    r = answers.get(nome)
    if not isinstance(r, dict):
        raise JevRespostaErro(f"O modelo não devolveu a resposta '{nome}'.")
    if "type" in r and r["type"] != tipo:
        raise JevRespostaErro(f"A resposta '{nome}' veio com o tipo errado.")
    return r


def _confianca(r):
    c = r.get("confidence")
    if isinstance(c, (int, float)) and not isinstance(c, bool):
        return float(c)
    return None


def parse_resposta(dados):
    answers = dados.get("answers") if isinstance(dados, dict) else None
    if not isinstance(answers, dict):
        raise JevRespostaErro("A resposta do modelo não tem o campo 'answers'.")

    r_tipo = _resposta(answers, "tipo_golpe", "choice")
    tipo = r_tipo.get("choice")
    if not isinstance(tipo, str) or tipo not in TIPOS_GOLPE:
        raise JevRespostaErro("O modelo escolheu um tipo de golpe desconhecido.")

    r_dados = _resposta(answers, "pede_dados", "noul")
    pede = _numero(r_dados.get("noul"), "noul")
    if not 0.0 <= pede <= 1.0:
        raise JevRespostaErro("A probabilidade 'noul' veio fora do intervalo de 0 a 1.")

    r_risco = _resposta(answers, "risco", "score")
    bruto = _numero(r_risco.get("score"), "score")
    nivel = math.floor(bruto + 0.5) + (1 if SCORE_COMECA_EM_ZERO else 0)
    nivel = max(1, min(5, nivel))

    conf_tipo = _confianca(r_tipo)
    if conf_tipo is None:
        probs = r_tipo.get("probabilities")
        p = probs.get(tipo) if isinstance(probs, dict) else None
        conf_tipo = float(p) if isinstance(p, (int, float)) and not isinstance(p, bool) else None
    return Analise(tipo=tipo, pede_dados=pede, risco=nivel, confianca=conf_tipo, confianca_risco=_confianca(r_risco))


_REGRAS_SIMULADAS = [
    (("boleto", "fatura", "cobrança"), "boleto_falso", 0.90, 4),
    (("senha", "código", "banco"), "phishing_bancario", 0.95, 4),
    (("prêmio", "sorteio", "ganhou"), "premio_falso", 0.85, 4),
    (("pix", "emprestado", "número novo"), "falso_suporte", 0.80, 3),
]


def _simular(mensagem):
    """Resposta falsa, no formato da API, só para desenvolvimento (JEV_MOCK=1)."""
    texto = mensagem.lower()
    for palavras, tipo, pede, score in _REGRAS_SIMULADAS:
        if any(p in texto for p in palavras):
            break
    else:
        tipo, pede, score = "mensagem_legitima", 0.05, 0
    return {
        "model": "jev-simulado",
        "answers": {
            "tipo_golpe": {"choice": tipo, "confidence": 0.9},
            "pede_dados": {"noul": pede},
            "risco": {"score": float(score), "confidence": 0.9},
        },
    }


def carregar_env(caminho=".env"):
    """Lê linhas NOME=valor de um .env simples, sem sobrescrever o que já está no ambiente."""
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            nome, valor = linha.split("=", 1)
            os.environ.setdefault(nome.strip(), valor.strip().strip('"').strip("'"))


def modo_simulado():
    return os.environ.get("JEV_MOCK") == "1"


def _mensagem_servidor(resposta):
    """Motivo do erro dado pelo servidor ({"error": {"message": ...}} ou {"message": ...}), se houver."""
    try:
        corpo = resposta.json()
    except ValueError:
        return ""
    if not isinstance(corpo, dict):
        return ""
    erro = corpo.get("error")
    erros = corpo.get("errors")  # formato da Cloudflare: {"errors": [{"code": ..., "message": ...}]}
    if isinstance(erro, dict):
        texto = erro.get("message")
    elif isinstance(erros, list) and erros and isinstance(erros[0], dict):
        texto = erros[0].get("message")
    else:
        texto = corpo.get("message")
    return texto[:200] if isinstance(texto, str) else ""


def chamar_api(mensagem, chave=None, base_url=None, modelo=None, http=requests):
    mensagem = validar_mensagem(mensagem)
    if modo_simulado():
        return _simular(mensagem)

    chave = chave or os.environ.get("JEV_API_KEY", "").strip()
    if not chave:
        raise JevConfigErro("Chave de API não configurada. Defina JEV_API_KEY no arquivo .env.")
    url = base_url or os.environ.get("JEV_BASE_URL") or BASE_URL_PADRAO
    modelo = modelo or os.environ.get("JEV_MODEL") or MODELO_PADRAO

    try:
        r = http.post(
            url,
            json=montar_requisicao(mensagem, modelo),
            headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.Timeout:
        raise JevErro("O modelo demorou demais para responder. Tente de novo.") from None
    except requests.RequestException:
        raise JevErro("Não foi possível falar com o modelo (problema de rede).") from None

    if r.status_code == 403 and _mensagem_servidor(r):
        raise JevErro(f"O provedor recusou o acesso: {_mensagem_servidor(r)}")
    if r.status_code in (401, 403):
        raise JevErro("O modelo recusou a chave de API (inválida ou sem permissão).")
    if r.status_code == 402:
        raise JevErro("A conta do provedor está sem crédito.")
    if r.status_code == 429:
        raise JevErro("Limite de uso do modelo atingido. Tente de novo em instantes.")
    if r.status_code >= 500:
        raise JevErro("O modelo está instável no momento. Tente de novo.")
    if r.status_code != 200:
        raise JevErro(f"O modelo respondeu com o erro {r.status_code}.")
    try:
        dados = r.json()
    except ValueError:
        raise JevRespostaErro("O modelo devolveu uma resposta que não é JSON.") from None
    if isinstance(dados, dict) and dados.get("success") is False:
        raise JevErro(f"O provedor recusou o pedido: {_mensagem_servidor(r) or 'sem detalhes'}")
    if isinstance(dados, dict) and "answers" not in dados and isinstance(dados.get("result"), dict):
        return dados["result"]  # a Cloudflare embrulha a resposta em {"result": {...}, "success": true}
    return dados


def consultar(mensagem, **opcoes):
    analise = parse_resposta(chamar_api(mensagem, **opcoes))
    return replace(analise, simulado=modo_simulado())
