class EtlError(Exception):
    """Falha de um ano; capturada só em pipeline.py (isolamento de FR-8)."""

    def __init__(self, ano: int | None, mensagem: str) -> None:
        super().__init__(f"{ano}: {mensagem}" if ano is not None else mensagem)
        self.ano = ano
        self.mensagem = mensagem
