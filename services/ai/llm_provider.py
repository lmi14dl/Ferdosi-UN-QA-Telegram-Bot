"""رابط عمومی ارائه‌دهندگان مدل زبانی"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class LLMResponse:
    text: str
    model: str
    success: bool
    error: Optional[str] = None
    usage: Optional[Dict] = None


class LLMProvider(ABC):
    """قرارداد مشترک برای همه ارائه‌دهندگان"""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        pass
