// Testa a Pages Function /analisar com um binding de IA falso (sem chamar a Cloudflare de verdade).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { onRequestPost } from "../functions/analisar.js";

const fx = JSON.parse(readFileSync(new URL("./fixtures/paridade.json", import.meta.url), "utf8"));
const respostaReal = fx.resposta.find((c) => c.nome === "clef_real_boleto").dados;

function chamar(corpo, env, bruto = false) {
  const request = new Request("https://guardagolpe.test/analisar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: bruto ? corpo : JSON.stringify(corpo),
  });
  return onRequestPost({ request, env });
}

function iaFalsa(resposta) {
  const chamadas = [];
  return { chamadas, AI: { run: async (modelo, entrada) => { chamadas.push({ modelo, entrada }); return resposta; } } };
}

test("devolve veredito, tipo e requisição no mesmo formato do Flask", async () => {
  const ia = iaFalsa(respostaReal);
  const r = await chamar({ mensagem: "  pague o boleto agora  " }, { AI: ia.AI });
  assert.equal(r.status, 200);
  const corpo = await r.json();
  assert.equal(corpo.veredito.nivel, "perigo");
  assert.equal(corpo.tipo_rotulo, "Boleto falso");
  assert.equal(corpo.analise.risco, 4);
  assert.equal(corpo.analise.simulado, false);
  assert.equal(corpo.requisicao.state, "pague o boleto agora");
  assert.equal(corpo.requisicao.model, "clef-flash");
});

test("chama o Workers AI com o modelo do Clef e a requisição montada", async () => {
  const ia = iaFalsa(respostaReal);
  await chamar({ mensagem: "oi" }, { AI: ia.AI });
  assert.equal(ia.chamadas.length, 1);
  assert.equal(ia.chamadas[0].modelo, "@cf/cloudflare/clef-flash");
  assert.deepEqual(Object.keys(ia.chamadas[0].entrada.questions).sort(), ["pede_dados", "risco", "tipo_golpe"]);
});

test("aceita a resposta embrulhada em {result: ...}", async () => {
  const r = await chamar({ mensagem: "oi" }, iaFalsa({ result: respostaReal, success: true }));
  assert.equal(r.status, 200);
});

test("mensagem vazia, longa demais ou corpo inválido dão 400", async () => {
  const env = iaFalsa(respostaReal);
  assert.equal((await chamar({ mensagem: "   " }, env)).status, 400);
  assert.equal((await chamar({ mensagem: "a".repeat(4001) }, env)).status, 400);
  assert.equal((await chamar("isso não é json", env, true)).status, 400);
  assert.equal((await chamar(["lista"], env)).status, 400);
  assert.equal(env.chamadas.length, 0, "não deve gastar IA com entrada inválida");
});

test("falha do modelo vira 502 com mensagem clara", async () => {
  const env = { AI: { run: async () => { throw new Error("detalhe interno secreto"); } } };
  const r = await chamar({ mensagem: "oi" }, env);
  assert.equal(r.status, 502);
  const { erro } = await r.json();
  assert.match(erro, /modelo/i);
  assert.ok(!erro.includes("secreto"), "não vaza detalhe interno");
});

test("resposta fora do formato vira 502", async () => {
  const r = await chamar({ mensagem: "oi" }, iaFalsa({ answers: [] }));
  assert.equal(r.status, 502);
});

test("sem o binding AI configurado dá 503", async () => {
  const r = await chamar({ mensagem: "oi" }, {});
  assert.equal(r.status, 503);
  assert.match((await r.json()).erro, /AI/);
});
