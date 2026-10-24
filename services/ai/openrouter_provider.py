"""اتصال به OpenRouter برای مدل‌های رایگان"""
import logging
import time
from typing import Optional
import requests
from services.ai.llm_provider import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-3.2-3b-instruct:free",
        timeout: int = 45,
        max_retries: int = 2,
    ):
        self._api_key = (api_key or "").strip()
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def model_id(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                text="",
                model=self._model,
                success=False,
                error="API Key تنظیم نشده است",
            )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/telegram-qa-bot",
            "X-Title": "University QA Bot",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = requests.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout,
                )
                if resp.status_code == 429:
                    last_error = "سهمیه یا محدودیت نرخ درخواست (429)"
                    time.sleep(2 ** attempt)
                    continue
                if resp.status_code >= 500:
                    last_error = f"خطای سرور ({resp.status_code})"
                    time.sleep(1)
                    continue
                if resp.status_code != 200:
                    try:
                        detail = resp.json()
                        last_error = detail.get("error", {}).get("message") or resp.text[:200]
                    except Exception:
                        last_error = resp.text[:200]
                    return LLMResponse(
                        text="", model=self._model, success=False, error=last_error
                    )

                data = resp.json()
                choices = data.get("choices") or []
                if not choices:
                    return LLMResponse(
                        text="", model=self._model, success=False, error="پاسخ خالی از مدل"
                    )
                text = (choices[0].get("message") or {}).get("content") or ""
                return LLMResponse(
                    text=text.strip(),
                    model=data.get("model", self._model),
                    success=True,
                    usage=data.get("usage"),
                )
            except requests.Timeout:
                last_error = "زمان پاسخ‌گویی مدل به پایان رسید (timeout)"
                logger.warning("OpenRouter timeout attempt %s", attempt)
            except requests.RequestException as e:
                last_error = f"خطای شبکه: {type(e).__name__}"
                logger.warning("OpenRouter network error: %s", e)
                time.sleep(1)

        return LLMResponse(
            text="", model=self._model, success=False, error=last_error or "خطای ناشناخته"
        )
