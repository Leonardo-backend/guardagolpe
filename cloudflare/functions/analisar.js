// Pages Function: POST /analisar
// Recebe {mensagem}, consulta o Clef pelo binding do Workers AI (sem chave de API) e devolve
// o mesmo JSON do app Flask: {analise, veredito, tipo_rotulo, requisicao}.
import { MODELO, MensagemInvalida, montarRequisicao, validarMensagem } from "./_lib/perguntas.js";
import { RespostaErro, parseResposta } from "./_lib/resposta.js";
import { ROTULOS, decidir } from "./_lib/decisao.js";

const MODELO_CF = "@cf/cloudflare/clef-flash";

const json = (corpo, status = 200) =>
  new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });

export async function onRequestPost({ request, env }) {
  let dados = null;
  try {
    dados = await request.json();
  } catch {
    dados = null;
  }
  if (dados === null || typeof dados !== "object" || Array.isArray(dados)) dados = {};

  let mensagem;
  try {
    mensagem = validarMensagem(dados.mensagem);
  } catch (erro) {
    if (erro instanceof MensagemInvalida) return json({ erro: erro.message }, 400);
    throw erro;
  }

  if (!env || !env.AI) return json({ erro: "O binding AI do Workers AI não está configurado neste projeto." }, 503);

  const requisicao = montarRequisicao(mensagem, MODELO);
  let bruto;
  try {
    bruto = await env.AI.run(MODELO_CF, requisicao);
  } catch {
    return json({ erro: "O modelo não respondeu. Tente de novo em instantes." }, 502);
  }
  // Pela API REST a Cloudflare embrulha a resposta em {result: {...}}; pelo binding ela vem direta.
  if (bruto && typeof bruto === "object" && !("answers" in bruto) && bruto.result && typeof bruto.result === "object") {
    bruto = bruto.result;
  }

  let analise;
  try {
    analise = parseResposta(bruto);
  } catch (erro) {
    if (erro instanceof RespostaErro) return json({ erro: `Resposta inesperada do modelo: ${erro.message}` }, 502);
    throw erro;
  }

  return json({
    analise,
    veredito: decidir(analise),
    tipo_rotulo: ROTULOS[analise.tipo],
    requisicao,
  });
}
