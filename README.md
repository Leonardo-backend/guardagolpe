# GuardaGolpe

Detector de golpes em mensagens (SMS, WhatsApp, e-mail). O usuário cola o texto e o sistema mostra se
ele **parece segura, pede atenção ou é perigosa**, o tipo provável de golpe e o que fazer.

A análise vem de um modelo de decisão do tipo *System One* (aqui, o **Clef**, da Cloudflare), que responde
três perguntas tipadas sobre a mensagem:

| Pergunta | Tipo | O que decide |
|---|---|---|
| `tipo_golpe` | Choice | Qual orientação mostrar (boleto falso, falso aviso do banco, falso suporte, prêmio falso, legítima) |
| `pede_dados` | Noul | Se pede dinheiro, senha, código ou clique (sim/não, em probabilidade) |
| `risco` | Score | O nível de risco, de 1 a 5, que define o semáforo |

A função `decidir()` (em `decisao.py`) combina as três respostas no veredito final. O formato de requisição
segue o do JEV (TypeSafe), mas **os testes reais foram feitos com o Clef**, não com o JEV.

> Este é um trabalho acadêmico (Fatec), não um produto de segurança. Um "parece segura" não garante nada:
> confirme sempre pelo canal oficial antes de pagar ou passar dados.

## Estrutura

| Caminho | O que é |
|---|---|
| `app.py` | Servidor Flask: `GET /` (página) e `POST /analisar` |
| `jev.py` | Cliente do modelo: monta a requisição, chama a API, lê e valida a resposta |
| `decisao.py` | Regras que transformam a resposta em veredito e orientação |
| `templates/index.html` | A página (tema escuro, sem rolagem no desktop) |
| `exemplos.py`, `rodar_exemplos.py` | Mensagens de exemplo e script que faz a consulta real e salva `prints/resultados.json` |
| `tests/` | 63 testes em Python |
| `cloudflare/` | Versão online no Cloudflare Pages (Function em JavaScript, 13 testes) |
| `gerar_site_cloudflare.py` | Gera a página e as fixtures de paridade da versão Cloudflare a partir do Flask |

## Rodar no seu computador

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt    # Linux/macOS: .venv/bin/python
cp .env.example .env                                         # e preencha o .env (veja abaixo)
.venv/Scripts/python -m pytest -q                            # 63 testes
.venv/Scripts/python app.py                                  # http://127.0.0.1:5000
```

Sem chave, dá para ver a interface com respostas **simuladas** (aparece uma etiqueta amarela "MODO SIMULADO"):

```bash
JEV_MOCK=1 .venv/Scripts/python app.py
```

## Configuração (`.env`)

O `.env` **nunca** vai para o Git. Para usar o Clef pela API REST da Cloudflare:

```
JEV_API_KEY=<token da API da Cloudflare, com permissão Workers AI>
JEV_BASE_URL=https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/cloudflare/clef-flash
JEV_MODEL=clef-flash
```

O `.env.example` traz também as linhas para o JEV direto (TypeSafe), para o Vercel AI Gateway e para o OpenRouter.
O plano gratuito da Cloudflare dá 10.000 neurons por dia no Workers AI (cerca de 3 mil consultas).

## Rodar numa máquina na nuvem (AWS EC2, por exemplo)

Passos padrão, **não testados numa instância AWS** por mim:

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone <URL-DESTE-REPOSITORIO> guardagolpe && cd guardagolpe
python3 -m venv .venv
.venv/bin/pip install flask requests gunicorn
cp .env.example .env && nano .env          # coloque o token e as variáveis da seção acima
.venv/bin/gunicorn -b 0.0.0.0:8000 "app:criar_app()"
```

Depois, no *Security Group* da instância, libere a porta **8000** (entrada TCP) só para o IP de quem vai ver,
e abra `http://<IP-PUBLICO-DA-INSTANCIA>:8000`.

Para um teste rápido sem gunicorn: `GUARDAGOLPE_HOST=0.0.0.0 .venv/bin/python app.py` (porta 5000).

Cuidados: o token fica só no `.env` do servidor. Não exponha a porta para a internet inteira, porque quem acessar
gasta a cota do token. Sem token, defina `JEV_MOCK=1` no `.env`: a interface funciona com respostas simuladas
(com a etiqueta "MODO SIMULADO" bem visível).

## Versão online (Cloudflare Pages)

Veja [`cloudflare/README.md`](cloudflare/README.md). Lá o modelo é chamado pelo binding do Workers AI, sem chave de API no código.

## Limitações conhecidas

- A avaliação feita até aqui foi com **3 mensagens de exemplo**. Não há dataset rotulado nem comparação com métodos clássicos.
- O modelo varia entre chamadas (a mesma mensagem já deu risco 1 e risco 2).
- A confiança do **Score** do Clef ficou entre 26% e 37% mesmo nas respostas corretas, então a regra de incerteza usa só a confiança do **Choice**.
