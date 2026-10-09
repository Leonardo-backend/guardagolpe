// Porte de jev.py: as três perguntas (Choice, Noul, Score) e a validação da mensagem.
// O resultado de montarRequisicao() é conferido contra o do Python em test/paridade.test.js.

export const MODELO = "clef-flash";
export const LIMITE_MENSAGEM = 4000;

export const TIPOS_GOLPE = {
  boleto_falso: "Boleto, fatura ou cobrança falsa, com link ou código de pagamento adulterado",
  phishing_bancario: "Falso aviso de banco ou cartão pedindo senha, código ou confirmação de dados",
  falso_suporte: "Falso atendente, suporte técnico ou parente pedindo dinheiro ou acesso ao aparelho",
  premio_falso: "Prêmio, sorteio, herança ou oferta boa demais para ser verdade",
  mensagem_legitima: "Mensagem comum, sem sinais de golpe",
};

export const NIVEIS_RISCO = [
  "Sem risco: mensagem normal, sem pedido suspeito",
  "Risco baixo: algum detalhe estranho, mas sem pedido de dados ou dinheiro",
  "Risco médio: sinais de golpe, como urgência ou link desconhecido",
  "Risco alto: pede dados, dinheiro ou clique, com urgência ou ameaça",
  "Risco crítico: golpe evidente, com link falso e pedido direto de dinheiro ou senha",
];

export class MensagemInvalida extends Error {}

export function validarMensagem(mensagem) {
  const texto = typeof mensagem === "string" ? mensagem.trim() : "";
  if (!texto) throw new MensagemInvalida("Cole uma mensagem para analisar.");
  if (texto.length > LIMITE_MENSAGEM) throw new MensagemInvalida(`A mensagem passa de ${LIMITE_MENSAGEM} caracteres.`);
  return texto;
}

export function montarRequisicao(mensagem, modelo = MODELO) {
  return {
    model: modelo,
    state: mensagem,
    questions: {
      tipo_golpe: {
        type: "choice",
        instructions: "A mensagem recebida é qual tipo de golpe? Escolha mensagem_legitima se não houver sinais de golpe.",
        criteria: { ...TIPOS_GOLPE },
      },
      pede_dados: {
        type: "noul",
        instructions: "A mensagem pede dinheiro, senha, código, dados pessoais ou um clique em link, de forma suspeita ou urgente?",
        criteria: {
          true: "Pede dinheiro, senha, código, dados pessoais ou clique em link",
          false: "Não pede nada disso",
        },
      },
      risco: {
        type: "score",
        instructions: "Qual o nível de risco de golpe da mensagem recebida?",
        criteria: [...NIVEIS_RISCO],
      },
    },
  };
}
