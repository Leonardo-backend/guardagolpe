import pytest

import decisao
import jev


def analise(tipo="mensagem_legitima", pede=0.0, risco=1, conf=0.9):
    return jev.Analise(tipo=tipo, pede_dados=pede, risco=risco, confianca=conf)


@pytest.mark.parametrize(
    "tipo,pede,risco,nivel",
    [
        ("mensagem_legitima", 0.05, 1, "segura"),
        ("mensagem_legitima", 0.10, 2, "segura"),
        ("mensagem_legitima", 0.80, 2, "atencao"),  # pede dados, mesmo com risco baixo
        ("falso_suporte", 0.30, 3, "atencao"),
        ("boleto_falso", 0.90, 4, "perigo"),
        ("phishing_bancario", 0.95, 5, "perigo"),
    ],
)
def test_nivel_do_veredito(tipo, pede, risco, nivel):
    assert decisao.decidir(analise(tipo, pede, risco)).nivel == nivel


def test_cores_e_titulos_por_nivel():
    assert decisao.decidir(analise(risco=1)).cor == "#059669"
    assert decisao.decidir(analise(risco=3)).cor == "#D97706"
    v = decisao.decidir(analise("boleto_falso", 0.9, 5))
    assert v.cor == "#B91C1C" and "golpe" in v.titulo.lower()


def test_orientacao_depende_do_tipo():
    v = decisao.decidir(analise("boleto_falso", 0.9, 5))
    assert any("boleto" in o.lower() for o in v.orientacao)
    v2 = decisao.decidir(analise("premio_falso", 0.9, 5))
    assert not any("boleto" in o.lower() for o in v2.orientacao)


def test_pedido_de_dados_acrescenta_alerta_de_senha():
    v = decisao.decidir(analise("falso_suporte", 0.9, 4))
    assert any("senha" in o.lower() for o in v.orientacao)
    sem = decisao.decidir(analise("mensagem_legitima", 0.1, 1))
    assert not any("nunca informe" in o.lower() for o in sem.orientacao)


def test_resultado_inconsistente_legitima_com_risco_alto():
    v = decisao.decidir(analise("mensagem_legitima", 0.2, 5))
    assert v.nivel == "perigo"
    assert any("inconsistente" in a.lower() for a in v.avisos)


def test_baixa_confianca_sobe_segura_para_atencao_e_avisa():
    v = decisao.decidir(analise("mensagem_legitima", 0.1, 1, conf=0.3))
    assert v.nivel == "atencao"
    assert any("incerto" in a.lower() for a in v.avisos)


def test_confianca_ausente_nao_gera_aviso():
    v = decisao.decidir(analise("mensagem_legitima", 0.1, 1, conf=None))
    assert v.nivel == "segura" and v.avisos == []


def test_todo_tipo_do_jev_tem_rotulo_e_orientacao():
    for tipo in jev.TIPOS_GOLPE:
        assert tipo in decisao.ROTULOS
        assert decisao.decidir(analise(tipo, 0.1, 1)).orientacao
