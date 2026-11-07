class ChatError(RuntimeError):
    """Technical chat failure with public metadata, never raw provider/DB details."""

    def __init__(
        self, code: str, *, stage: str, retryable: bool = False, status_code: int = 503,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.stage = stage
        self.retryable = retryable
        self.status_code = status_code

    def public_payload(self) -> dict[str, object]:
        return {"code": self.code, "retryable": self.retryable}


class RetrievalError(ChatError):
    def __init__(self, code: str = "RETRIEVAL_UNAVAILABLE", *, stage: str = "retrieval", retryable: bool = True) -> None:
        super().__init__(code, stage=stage, retryable=retryable)


class ConversationStateError(ChatError):
    def __init__(self, *, stage: str, corrupt: bool = False) -> None:
        super().__init__(
            "STATE_CORRUPTED" if corrupt else "STATE_UNAVAILABLE",
            stage=stage, retryable=not corrupt,
        )


class ChatConfigurationError(ChatError):
    def __init__(self, code: str, *, stage: str) -> None:
        super().__init__(code, stage=stage)


class UnexpectedChatError(ChatError):
    def __init__(self, *, stage: str) -> None:
        super().__init__("INTERNAL_ERROR", stage=stage, status_code=500)
