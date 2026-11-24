from pydantic import BaseModel, ConfigDict, Field, UUID4


class ChatRequest(BaseModel):
    """Request body for the streaming conversation message endpoint."""

    model_config = ConfigDict(extra="forbid")

    client_request_id: UUID4
    text: str = Field(min_length=1, max_length=4000)
    expected_version: int | None = Field(default=None, ge=0)

