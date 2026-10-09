"""Gera o PDF de entrega a partir de prints/resultados.json e dos prints reais."""
import json
import os
import sys
import textwrap
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

import jev

PASTA = os.path.dirname(os.path.abspath(__file__))
PRINTS = os.path.join(PASTA, "prints")
SAIDA = os.path.join(PASTA, "Atividade_JEV_GuardaGolpe.pdf")
NOME = "GuardaGolpe"
AZUL = colors.HexColor("#1d4ed8")
CINZA = colors.HexColor("#6b7280")

FIGURAS = [
    ("01_tela_inicial.png", "Figura 1 - Tela inicial do GuardaGolpe: área para colar a mensagem suspeita e botões com mensagens de exemplo."),
    ("02_exemplo_preenchido.png", "Figura 2 - Dados do teste: o exemplo \"Boleto falso\" colado na área de texto, pronto para ser analisado."),
    ("03_resultado_boleto.png", "Figura 3 - Resultado obtido para o exemplo \"Boleto falso\": veredito, tipo de golpe (Choice), pedido de dados (Noul), nível de risco (Score), confiança do modelo e orientação do que fazer."),
    ("04_resultado_legitima.png", "Figura 4 - Resultado obtido para o exemplo \"Mensagem legítima\", pelo mesmo fluxo, para comparar com a figura 3."),
    ("05_requisicao.png", "Figura 5 - Janela \"Ver requisição\": o que foi enviado ao modelo (o texto da mensagem e as três perguntas Choice, Noul e Score), sem a chave de API."),
]

base = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=base["Heading1"], fontSize=16, textColor=AZUL, spaceBefore=14, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=base["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
TXT = ParagraphStyle("TXT", parent=base["BodyText"], fontSize=10.5, leading=14.5, spaceAfter=6)
LEG = ParagraphStyle("LEG", parent=TXT, fontSize=9, leading=12, textColor=CINZA, spaceAfter=14)
TITULO = ParagraphStyle("TITULO", parent=base["Title"], fontSize=30, leading=38, textColor=AZUL, spaceAfter=10)
SUB = ParagraphStyle("SUB", parent=TXT, fontSize=14, textColor=CINZA, alignment=1)
NOMES = ParagraphStyle("NOMES", parent=TXT, fontSize=13, alignment=1, spaceAfter=3)
CELULA = ParagraphStyle("CELULA", parent=TXT, fontSize=8.5, leading=11, spaceAfter=0)
CODIGO = ParagraphStyle("CODIGO", parent=base["Code"], fontName="Courier", fontSize=6.5, leading=7.6)


def p(texto, estilo=TXT):
    return Paragraph(texto, estilo)


def lista(itens):
    return [p("&bull; " + i) for i in itens]


def ler_integrantes():
    caminho = os.path.join(PASTA, "integrantes.txt")
    if not os.path.exists(caminho):
        sys.exit("Crie integrantes.txt com um nome por linha (de 1 a 4).")
    with open(caminho, encoding="utf-8") as f:
        nomes = [l.strip() for l in f if l.strip()]
    if not 1 <= len(nomes) <= 4:
        sys.exit("integrantes.txt precisa ter de 1 a 4 nomes.")
    return nomes


def ler_resultados():
    caminho = os.path.join(PRINTS, "resultados.json")
    if not os.path.exists(caminho):
        sys.exit("Falta prints/resultados.json. Rode rodar_exemplos.py com a chave real.")
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    if dados.get("simulado"):
        sys.exit("Os resultados são simulados e não podem ir para o PDF.")
    return dados


def quebrar_linhas(texto, largura=118):
    """Quebra linhas longas do JSON mantendo a indentação, para não estourar a margem do PDF."""
    saida = []
    for linha in texto.splitlines():
        recuo = len(linha) - len(linha.lstrip())
        saida += textwrap.wrap(linha, width=largura, subsequent_indent=" " * (recuo + 4),
                               break_long_words=True, replace_whitespace=False, drop_whitespace=False) or [""]
    return "\n".join(saida)


def figura(nome, legenda, largura_max=15.5 * cm, altura_max=10.3 * cm):
    caminho = os.path.join(PRINTS, nome)
    if not os.path.exists(caminho):
        sys.exit(f"Falta o print prints/{nome}.")
    w, h = ImageReader(caminho).getSize()
    escala = min(largura_max / w, altura_max / h)
    img = Image(caminho, width=w * escala, height=h * escala)
    img.hAlign = "CENTER"
    return KeepTogether([img, Spacer(1, 4), p(escape(legenda), LEG)])


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(CINZA)
    canvas.drawString(2 * cm, 1.2 * cm, f"{NOME} - detector de golpes em mensagens")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def tabela_resultados(exemplos):
    def pct(v):
        return "n/d" if v is None else f"{round(v * 100)}%"

    linhas = [["Exemplo", "Esperado", "Veredito", "Tipo (Choice)", "Pede dados (Noul)", "Risco (Score)",
               "Conf. do tipo", "Conf. do risco"]]
    for e in exemplos:
        linhas.append([e["titulo"], e["esperado"], e["veredito"], e["tipo_rotulo"],
                       pct(e["pede_dados"]), f"{e['risco']} / 5", pct(e["confianca"]), pct(e.get("confianca_risco"))])
    linhas = [[p(escape(str(c)), CELULA) for c in l] for l in linhas]
    t = Table(linhas, repeatRows=1, colWidths=[2.5 * cm, 1.9 * cm, 1.7 * cm, 3.0 * cm, 2.0 * cm, 1.7 * cm, 2.0 * cm, 2.1 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ]))
    return t


def tabela_regras():
    linhas = [
        ["Condição (resposta do modelo)", "Decisão do sistema"],
        ["Score 4 ou 5", "Perigo (vermelho)"],
        ["Score 3, ou Noul indica pedido de dados (50% ou mais)", "Atenção (amarelo)"],
        ["Score 1 ou 2 e sem pedido de dados", "Parece segura (verde)"],
        ["Choice escolhe o tipo de golpe", "Define o texto de orientação (ex.: boleto falso: conferir o código de barras no app do banco)"],
        ["Choice diz \"legítima\" mas Score é 4 ou 5", "Aviso de resultado inconsistente: tratar como suspeita"],
        ["Confiança do modelo no tipo (Choice) abaixo de 50%", "Aviso de incerteza: tratar como suspeita (uma mensagem segura sobe para Atenção)"],
    ]
    linhas = [[p(escape(c), CELULA) for c in l] for l in linhas]
    t = Table(linhas, colWidths=[7.5 * cm, 9.5 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def conclusao(dados):
    exemplos = dados["exemplos"]
    acertos = sum(1 for e in exemplos if e["veredito"] == e["esperado"])
    total = len(exemplos)
    itens = [
        f"Teste feito em {dados['data']}, no provedor {escape(dados['provedor'])}, "
        f"modelo {escape(str(dados.get('modelo_respondido') or dados['modelo']))}, com uma consulta real por exemplo.",
        f"{acertos} de {total} exemplos receberam o veredito esperado.",
    ]
    confs_risco = [e["confianca_risco"] for e in exemplos if e.get("confianca_risco") is not None]
    if confs_risco and max(confs_risco) < 0.5:
        itens.append(
            "<b>Ajuste feito depois do primeiro teste real:</b> a primeira versão da regra de incerteza usava a menor "
            "confiança entre o Choice e o Score. Nos testes, a confiança do Score ficou entre "
            f"{round(min(confs_risco) * 100)}% e {round(max(confs_risco) * 100)}%, mesmo quando as probabilidades "
            "apontavam claramente o nível de risco. Com essa regra, toda mensagem seria marcada como incerta e o "
            "veredito \"parece segura\" nunca apareceria (a mensagem legítima do teste saiu como \"atenção\"). "
            "Passamos a usar só a confiança do Choice, e guardamos a do Score à parte (coluna \"Conf. do risco\" "
            "da tabela). O ajuste foi feito depois de ver o resultado e está registrado aqui por isso."
        )
    for e in exemplos:
        if e["veredito"] != e["esperado"]:
            itens.append(f"Divergência: o exemplo \"{escape(e['titulo'])}\" era esperado como {e['esperado']}, "
                         f"mas o sistema mostrou {e['veredito']} (risco {e['risco']} de 5). "
                         "Mantivemos o resultado real, sem ajustar o exemplo.")
    return itens


def montar(integrantes, dados, saida=SAIDA):
    doc = SimpleDocTemplate(saida, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=f"{NOME} - Atividade JEV",
                            author=", ".join(integrantes))
    s = []

    # Capa: nome do sistema e integrantes
    s += [Spacer(1, 5 * cm), p(NOME, TITULO), p("Detector de golpes em mensagens, com modelo de decisão System One", SUB), Spacer(1, 1.5 * cm),
          p("<b>Integrantes</b>", NOMES)] + [p(escape(n), NOMES) for n in integrantes] + [PageBreak()]

    # 1. O que o sistema faz
    s += [p("1. O que o sistema faz", H1),
          p("O GuardaGolpe analisa uma mensagem recebida por SMS, WhatsApp ou e-mail e diz se ela parece golpe. "
            "O usuário cola o texto, clica em \"Analisar mensagem\" e recebe um veredito (parece segura, atenção ou perigo), "
            "o tipo provável de golpe e uma orientação do que fazer."),
          p("<b>Problema que resolve:</b> muita gente recebe mensagens com boleto falso, aviso de banco falso, pedido de "
            "dinheiro de falso parente ou prêmio falso e não sabe dizer se são confiáveis. O sistema dá uma segunda opinião "
            "rápida antes de a pessoa clicar, pagar ou passar uma senha."),
          p("<b>Quem pode usar:</b> qualquer pessoa, em especial quem tem menos familiaridade com golpes digitais, como "
            "familiares mais velhos, e também equipes de atendimento que precisam triar mensagens suspeitas de clientes.")]

    # 2. Funcionamento
    requisicao = quebrar_linhas(json.dumps(
        jev.montar_requisicao("<texto da mensagem colada pelo usuário>", dados["modelo"]), ensure_ascii=False, indent=2))
    modelo = escape(str(dados.get("modelo_respondido") or dados["modelo"]))
    provedor = escape(dados["provedor"])
    s += [p("2. Como funciona", H1),
          p(f"<b>Modelo usado nos testes:</b> {modelo}, pelo provedor {provedor}. O trabalho pede o JEV, mas o acesso ao JEV "
            "exige depósito mínimo (US$ 5 na TypeSafe e US$ 10 na Vercel, que testamos) e o grupo optou por não pagar "
            "esse valor só para um trabalho acadêmico. Por isso usamos um modelo de decisão \"System One\" da mesma categoria, que recebe um texto (state) e "
            "perguntas tipadas Choice, Noul e Score e devolve decisões com probabilidade e confiança. O sistema foi "
            "escrito seguindo o formato de requisição do JEV (código do Laboratório JEV e documentação da TypeSafe); "
            "<b>não chegamos a consultar o JEV em si</b>. Trocar de modelo exige só mudar o endereço e o nome do modelo "
            "na configuração."),
          p("<b>O que o usuário informa:</b> apenas o texto da mensagem suspeita (até 4000 caracteres). "
            "Há botões com mensagens de exemplo para testar."),
          p("<b>O que é enviado ao modelo:</b> uma única consulta (POST) com o texto da mensagem e três perguntas, "
            "cada uma de um tipo estudado no JEV (Choice, Noul ou Score). A chave de API fica só no servidor e nunca aparece na tela. "
            "Abaixo, a requisição real montada pelo sistema:"),
          Preformatted(requisicao, CODIGO),
          Spacer(1, 6),
          p("<b>Tipos de pergunta do JEV escolhidos e motivo:</b> usamos os três (Choice, Noul e Score), cada um para um papel diferente.")]
    s += lista([
        "<b>Choice (tipo_golpe):</b> o modelo precisa escolher uma entre cinco categorias fixas (boleto falso, falso aviso do "
        "banco, falso suporte, prêmio falso, mensagem legítima). Escolhemos o Choice porque a classificação em categorias "
        "define qual orientação mostrar ao usuário.",
        "<b>Noul (pede_dados):</b> é uma pergunta de sim ou não, devolvida como probabilidade: a mensagem pede dinheiro, "
        "senha, código ou clique? Escolhemos o Noul porque esse pedido é o sinal mais forte de golpe e merece um alerta próprio.",
        "<b>Score (risco):</b> o modelo escolhe um nível de risco de 1 a 5. Escolhemos o Score porque o sistema precisa de uma "
        "gradação para decidir a cor do semáforo e o veredito final.",
    ])
    s += [p("<b>Como a resposta é usada:</b> o sistema não só mostra o que o modelo respondeu; ele decide com isso, pela função "
            "<i>decidir</i>:"),
          tabela_regras()]

    # 3. Prints
    s += [PageBreak(), p("3. Telas do sistema em funcionamento", H1),
          p("As telas abaixo foram tiradas do sistema rodando, com consultas reais ao modelo. A chave de API não aparece em nenhuma.")]
    s += [figura(n, l, altura_max=(8.6 * cm if n.startswith("05") else 10.3 * cm)) for n, l in FIGURAS]
    s += [p("Resultados dos três exemplos testados", H2), tabela_resultados(dados["exemplos"]), Spacer(1, 8)]

    # 4. Conclusão
    s += [p("4. Conclusão e melhoria", H1)] + [p(t) for t in conclusao(dados)] + [
          p("<b>Melhoria que o grupo faria:</b> permitir enviar um print da conversa (imagem) em vez de só texto colado, e guardar "
            "um histórico das análises para o usuário comparar mensagens parecidas e acompanhar golpes que se repetem.")]

    doc.build(s, onFirstPage=lambda c, d: None, onLaterPages=rodape)


def main():
    montar(ler_integrantes(), ler_resultados())
    print(f"PDF gerado: {SAIDA}")


if __name__ == "__main__":
    main()
