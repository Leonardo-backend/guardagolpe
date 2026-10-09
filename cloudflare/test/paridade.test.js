// Confere se o porte em JavaScript dá exatamente o mesmo resultado do Python.
// As fixtures vêm de gerar_site_cloudflare.py (saídas do jev.py e do decisao.py).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { montarRequisicao, validarMensagem, MensagemInvalida, LIMITE_MENSAGEM } from "../functions/_lib/perguntas.js";
import { parseResposta, RespostaErro } from "../functions/_lib/resposta.js";
import { decidir, ROTULOS } from "../functions/_lib/decisao.js";

const fx = JSON.parse(readFileSync(new URL("./fixtures/paridade.json", import.meta.url), "utf8"));

test("a requisição montada é idêntica à do Python", () => {
  const { mensagem, modelo, esperado } = fx.requisicao;
  assert.deepStrictEqual(montarRequisicao(mensagem, modelo), esperado);
});

test("a requisição respeita os limites do modelo", () => {
  const q = montarRequisicao("x", "clef-flash").questions;
  assert.deepEqual(Object.keys(q).sort(), ["pede_dados", "risco", "tipo_golpe"]);
  const ids = Object.keys(q.tipo_golpe.criteria);
  assert.ok(ids.length >= 2 && ids.length <= 8);
  assert.ok(ids.every((id) => /^[a-z][a-z0-9_]{0,29}$/.test(id)));
  assert.equal(q.risco.criteria.length, 5);
  for (const p of Object.values(q)) assert.ok(p.instructions.length <= 500);
});

test("os rótulos dos tipos de golpe são iguais aos do Python", () => {
  assert.deepStrictEqual(ROTULOS, fx.rotulos);
});

test(`decidir() dá o mesmo veredito do Python nos ${fx.decisao.length} casos`, () => {
  for (const { entrada, esperado } of fx.decisao) {
    assert.deepStrictEqual(decidir(entrada), esperado, JSON.stringify(entrada));
  }
});

test("parseResposta() lê as respostas como o Python (incluindo as reais do Clef)", () => {
  for (const { nome, dados, esperado } of fx.resposta) {
    if (esperado.erro) {
      assert.throws(() => parseResposta(dados), RespostaErro, nome);
    } else {
      assert.deepStrictEqual(parseResposta(dados), esperado, nome);
    }
  }
});

test("validarMensagem() tira espaços e recusa vazio ou longo demais", () => {
  assert.equal(validarMensagem("  oi  "), "oi");
  for (const ruim of ["", "   ", null, undefined, 42, "a".repeat(LIMITE_MENSAGEM + 1)]) {
    assert.throws(() => validarMensagem(ruim), MensagemInvalida);
  }
  assert.equal(validarMensagem("a".repeat(LIMITE_MENSAGEM)).length, LIMITE_MENSAGEM);
});
