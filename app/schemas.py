from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class LLMResponse(BaseModel):
    completion: str
    model: str
    fallback: bool = False
    circuit_state: str | None = None
    reason: str | None = None
