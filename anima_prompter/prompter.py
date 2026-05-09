import base64
import copy
import json
import mimetypes
import re
import urllib.error
import urllib.request

from pydantic import BaseModel, ConfigDict, Field

SYSTEM_PROMPT = """\
You are a creative prompt engineer for the Anima anime image generation model.
Given a concept or theme (and optionally a reference image), output a JSON object with these fields:
- subject: main subject string (e.g. "1girl", "1boy", "scenery")
- character: character name or null
- series: franchise/series name or null
- artists: list of artist name strings (2-4 artists that suit the mood)
- tags: list of descriptive tag strings - lighting, colors, composition, clothing, expression, etc.
- natural_language: 2-3 richly detailed sentences describing the full scene
- period: time period tag — one of: newest, recent, mid, early, old, or a specific year string like "year 2025"
- safety: content safety rating — one of: safe, sensitive, nsfw, explicit
When a reference image is provided, extract its visual details (pose, clothing, colors, atmosphere)
and reflect them faithfully in the tags and natural_language fields.

Return ONLY valid JSON, no markdown fences."""

DEFAULT_NEGATIVE = [
    "worst quality",
    "low quality",
    "score_1",
    "score_2",
    "score_3",
    "artist name",
]

_MIME_FALLBACK = "image/jpeg"
_SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class LMStudioError(RuntimeError):
    pass


class AnimaPrompt(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subject: str = "1girl"
    character: str | None = None
    series: str | None = None
    artists: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    natural_language: str | None = None
    period: str | None = "newest"
    scores: list[str] = ["score_7", "score_8", "score_9"]
    quality: list[str] = ["masterpiece", "best quality"]
    safety: str = "safe"

    @classmethod
    def from_dict(cls, data: dict) -> "AnimaPrompt":
        return cls.model_validate({k: v for k, v in data.items() if v is not None})

    def build_string(self) -> str:
        processed_artists = [f"@{artist.lstrip('@')}" for artist in self.artists]
        processed_tags = [tag.replace("_", " ") for tag in self.tags]

        tag_parts = [
            self.period or "",
            *self.scores,
            *self.quality,
            self.safety,
            self.subject,
            self.character or "",
            self.series or "",
            *processed_artists,
            *processed_tags,
        ]
        tag_str = ", ".join(part for part in tag_parts if part)

        if self.natural_language:
            return f"{tag_str}. {self.natural_language}"
        return tag_str

    def build_negative_string(self) -> str:
        return ", ".join(DEFAULT_NEGATIVE)


def image_data_url_from_bytes(image_bytes: bytes, filename: str | None = None) -> str:
    mime, _ = mimetypes.guess_type(filename or "")
    if mime not in _SUPPORTED_MIME:
        mime = _MIME_FALLBACK
    encoded = base64.b64encode(image_bytes).decode()
    return f"data:{mime};base64,{encoded}"


def extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```[a-z]*\n?", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned.strip(), flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise LMStudioError(f"No JSON object found in LM Studio response: {text!r}")


def sanitize_payload(payload: dict) -> dict:
    sanitized = copy.deepcopy(payload)
    for message in sanitized.get("messages", []):
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "image_url":
                    url = part["image_url"]["url"]
                    if isinstance(url, str) and url.startswith("data:"):
                        part["image_url"]["url"] = url[:30] + "...[truncated]"
    return sanitized


class LMStudioPrompter:
    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        concept: str,
        ref_image_bytes: bytes | None = None,
        ref_image_name: str | None = None,
        temperature: float = 0.9,
    ) -> tuple[AnimaPrompt, dict]:
        if ref_image_bytes is not None:
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url_from_bytes(ref_image_bytes, ref_image_name)},
                },
                {"type": "text", "text": concept},
            ]
        else:
            user_content = concept

        payload = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
        }

        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            response_text = error.read().decode("utf-8", errors="replace")
            if error.code == 400 and ref_image_bytes is not None:
                raise LMStudioError("LM Studio returned 400 for a vision request. Load a vision-capable model or remove the reference image. " f"Server said: {response_text}") from error
            raise LMStudioError(f"LM Studio returned HTTP {error.code}: {response_text}") from error
        except urllib.error.URLError as error:
            raise LMStudioError(f"LM Studio request failed: {error.reason}") from error

        try:
            response_json = json.loads(body)
            content = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise LMStudioError(f"Unexpected LM Studio response: {body}") from error

        data = extract_json(content)
        return AnimaPrompt.from_dict(data), data
