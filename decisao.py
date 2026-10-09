"""Transforma a resposta do JEV numa decisão do sistema: veredito, cor e orientação."""
from dataclasses import dataclass

LIMITE_PEDE_DADOS = 0.5
LIMITE_CONFIANCA = 0.5

ROTULOS = {
    "boleto_falso": "Boleto falso",
    "phishing_bancario": "Falso aviso do banco",
    "falso_suporte": "Falso suporte ou pedido de dinheiro",
    "premio_falso": "Prêmio ou sorteio falso",
    "mensagem_legitima": "Mensagem legítima",
}

ORIENTACOES = {
    "boleto_falso": [
        "Não pague pelo link da mensagem.",
        "Confira o boleto no app ou no site oficial do banco ou da empresa.",
        "Compare o código de barras com o da cobrança original.",
    ],
    "phishing_bancario": [
        "Não clique no link e não responda a mensagem.",
        "Abra o app do seu banco digitando o endereço você mesmo, ou ligue para o número do cartão.",
        "Bancos não pedem senha nem código por mensagem.",
    ],
    "falso_suporte": [
        "Não faça Pix nem transferência antes de confirmar por ligação, no número que você já tinha.",
        "Não instale aplicativos nem passe acesso ao seu aparelho.",
    ],
    "premio_falso": [
        "Não clique no link. Prêmio de sorteio que você não disputou não existe.",
        "Não pague taxa para liberar prêmio ou herança.",
    ],
    "mensagem_legitima": [
        "Nenhum sinal de golpe encontrado.",
        "Mesmo assim, confirme pelo canal oficial antes de enviar dinheiro ou dados.",
    ],
}

TITULOS = {
    "segura": "Parece segura",
    "atencao": "Atenção: desconfie",
    "perigo": "Perigo: provável golpe",
}

CORES = {"segura": "#059669", "atencao": "#D97706", "perigo": "#B91C1C"}


@dataclass(frozen=True)
class Veredito:
    nivel: str
    titulo: str
    cor: str
    orientacao: list
    avisos: list


def decidir(analise):
    """Combina Choice (tipo), Noul (pede dados) e Score (risco) numa decisão."""
    if analise.risco >= 4:
        nivel = "perigo"
    elif analise.risco == 3 or analise.pede_dados >= LIMITE_PEDE_DADOS:
        nivel = "atencao"
    else:
        nivel = "segura"

    avisos = []
    if analise.tipo == "mensagem_legitima" and analise.risco >= 4:
        avisos.append(
            "Resultado inconsistente: o modelo classificou como legítima, mas apontou risco alto. "
            "Trate como suspeita."
        )
    if analise.confianca is not None and analise.confianca < LIMITE_CONFIANCA:
        avisos.append("O modelo está incerto sobre esta mensagem. Trate como suspeita.")
        if nivel == "segura":
            nivel = "atencao"

    orientacao = list(ORIENTACOES[analise.tipo])
    if analise.pede_dados >= LIMITE_PEDE_DADOS:
        orientacao.append("Nunca informe senhas, códigos ou dados de cartão por mensagem.")

    return Veredito(nivel=nivel, titulo=TITULOS[nivel], cor=CORES[nivel], orientacao=orientacao, avisos=avisos)
