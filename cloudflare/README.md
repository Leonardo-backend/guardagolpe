# GuardaGolpe no Cloudflare Pages

Versão online do GuardaGolpe. A página é a mesma do app Flask; o backend é uma Pages Function
(`functions/analisar.js`) que consulta o **Clef** pelo binding do Workers AI. Não há chave de API
no código nem no navegador: a autorização vem do próprio projeto na conta da Cloudflare.

## Estrutura

| Caminho | O que é |
|---|---|
| `public/index.html` | A página (gerada a partir do template do Flask) |
| `functions/analisar.js` | `POST /analisar`: valida, chama o Clef, devolve o veredito |
| `functions/_lib/` | Porte do `jev.py` e do `decisao.py` para JavaScript |
| `test/` | Testes; as fixtures vêm do Python para garantir resultados idênticos |
| `wrangler.toml` | Nome do projeto e binding `AI` |

## Rodar os testes

```bash
cd cloudflare
npm test
```

## Atualizar a página ou as fixtures (depois de mexer no Python)

Na pasta do projeto (`Atividade_JEV_DetectorGolpes`):

```bash
.venv/Scripts/python gerar_site_cloudflare.py
```

## Publicar

```bash
cd cloudflare
npx wrangler login
npx wrangler pages project create guardagolpe --production-branch main
npx wrangler pages deploy public --project-name guardagolpe
```

O arrastar-e-soltar do painel **não** serve: ele não compila a pasta `functions`.

## Limites

O plano gratuito da Cloudflare dá 10.000 neurons por dia no Workers AI (cerca de 3 mil consultas
com o `clef-flash`). Passando disso, as consultas falham até o dia seguinte; nada é cobrado no plano gratuito.
Quem tiver o link pode gastar essa cota, então compartilhe o endereço só com quem precisa.
