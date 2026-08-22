"""
Сообщение диалога с языковой моделью.
"""

from pydantic import BaseModel, ConfigDict

from src.back.l01_domain.llm.constants import ChatRole


class ChatMessage(BaseModel):
    """Одно сообщение диалога."""

    model_config = ConfigDict(frozen=True)

    role: ChatRole
    content: str

    def to_payload(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}
