"""Mensagens de exemplo usadas na interface e no teste real (rodar_exemplos.py)."""

EXEMPLOS = [
    {
        "id": "boleto",
        "titulo": "Boleto falso",
        "texto": (
            "URGENTE: seu boleto do cartão está vencido e seu nome será negativado hoje. "
            "Pague agora pelo link https://segunda-via-boleto.xyz/pagar para evitar protesto. "
            "Atenciosamente, Central de Cobrança."
        ),
        "esperado": "perigo",
    },
    {
        "id": "banco",
        "titulo": "Aviso do banco",
        "texto": (
            "Banco Nacional: detectamos um acesso suspeito na sua conta. Para evitar o bloqueio, "
            "confirme sua senha e o código enviado por SMS em http://bn-seguranca-app.com/confirmar"
        ),
        "esperado": "perigo",
    },
    {
        "id": "legitima",
        "titulo": "Mensagem legítima",
        "texto": (
            "Oi! Aqui é da secretaria da Fatec. A aula de sexta-feira foi remarcada para as 19h "
            "na sala 12. Nenhuma ação é necessária, só avisando."
        ),
        "esperado": "segura",
    },
]
