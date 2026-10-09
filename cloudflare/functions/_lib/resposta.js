// Porte de jev.parse_resposta(): lê a resposta do modelo e normaliza (tipo, pede dados, risco 1-5, confianças).
import { TIPOS_GOLPE } from "./perguntas.js";

export class RespostaErro extends Error {}

const ehNumero = (v) => typeof v === "number" && Number.isFinite(v);
const ehObjeto = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

function numero(valor, nome) {
  if (typeof valor === "boolean") return valor ? 1 : 0;
  if (ehNumero(valor)) return valor;
  throw new RespostaErro(`O campo '${nome}' veio em formato inesperado.`);
}

function resposta(answers, nome, tipo) {
  const r = answers[nome];
  if (!ehObjeto(r)) throw new RespostaErro(`O modelo não devolveu a resposta '${nome}'.`);
  if ("type" in r && r.type !== tipo) throw new RespostaErro(`A resposta '${nome}' veio com o tipo errado.`);
  return r;
}

const confianca = (r) => (ehNumero(r.confidence) ? r.confidence : null);

export function parseResposta(dados) {
  const answers = ehObjeto(dados) ? dados.answers : undefined;
  if (!ehObjeto(answers)) throw new RespostaErro("A resposta do modelo não tem o campo 'answers'.");

  const rTipo = resposta(answers, "tipo_golpe", "choice");
  const tipo = rTipo.choice;
  if (typeof tipo !== "string" || !Object.hasOwn(TIPOS_GOLPE, tipo)) {
    throw new RespostaErro("O modelo escolheu um tipo de golpe desconhecido.");
  }

  const pede = numero(resposta(answers, "pede_dados", "noul").noul, "noul");
  if (pede < 0 || pede > 1) throw new RespostaErro("A probabilidade 'noul' veio fora do intervalo de 0 a 1.");

  const rRisco = resposta(answers, "risco", "score");
  const bruto = numero(rRisco.score, "score");
  // A escala do score começa em 0 (confirmado nas respostas reais): nível = arredondado + 1, entre 1 e 5.
  const risco = Math.max(1, Math.min(5, Math.floor(bruto + 0.5) + 1));

  let confTipo = confianca(rTipo);
  if (confTipo === null && ehObjeto(rTipo.probabilities) && ehNumero(rTipo.probabilities[tipo])) {
    confTipo = rTipo.probabilities[tipo];
  }
  return { tipo, pede_dados: pede, risco, confianca: confTipo, simulado: false, confianca_risco: confianca(rRisco) };
}
