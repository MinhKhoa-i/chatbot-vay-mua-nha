from pydantic import BaseModel, ConfigDict, Field, UUID4


class ChatRequest(BaseModel):
    """Request body for the streaming conversation message endpoint."""

    model_config = ConfigDict(extra="forbid")

    client_request_id: UUID4
    text: str = Field(min_length=1, max_length=4000)
    expected_version: int | None = Field(default=None, ge=0)

    @property
    def message(self) -> str:
        return self.text


class EstimateResponse(BaseModel):
    amount: int | float
    years: int
    rate: float
    monthly_payment: int
    total_interest: int


class CitationResponse(BaseModel):
    source_id: str
    title: str
    url: str
    verified_on: str | None = None


class ChatResponse(BaseModel):
    reply: str
    updated_at: str
    estimate: EstimateResponse | None = None
    intents: list[str] = Field(default_factory=list)
    clarification_needed: bool = False
    citations: list[CitationResponse] = Field(default_factory=list)
