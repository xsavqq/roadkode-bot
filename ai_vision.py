import base64
import json
import os

import aiohttp


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")


async def estimate_weight_from_image(image_bytes: bytes) -> dict:
    """
    Оценивает примерный вес товара по фотографии.

    Возвращает:
    {
        "product_type": "...",
        "min_kg": 0.2,
        "max_kg": 0.5,
        "confidence": "low|medium|high",
        "note": "..."
    }
    """

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
Проанализируй фотографию товара и оцени его примерный вес.

ВАЖНО:
- Вес нужен БЕЗ упаковки.
- Если на фото несколько одинаковых товаров, оцени вес ОДНОЙ штуки.
- Не придумывай точный вес. Всегда используй разумный диапазон.
- Если по фотографии невозможно уверенно определить вес, используй широкий диапазон.
- Учитывай тип товара, материал, размер и конструкцию.
- Ответ должен быть только в JSON.

Формат ответа:

{
  "product_type": "краткое название товара",
  "min_kg": 0.2,
  "max_kg": 0.5,
  "confidence": "low",
  "note": "краткое объяснение на русском"
}

confidence должен быть только:
low
medium
high

min_kg и max_kg должны быть положительными числами.
"""

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                    {
                        "type": "input_image",
                        "image_url": (
                            f"data:image/jpeg;base64,{image_base64}"
                        ),
                        "detail": "low",
                    },
                ],
            }
        ],
    }

    timeout = aiohttp.ClientTimeout(total=45)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as response:

            response_text = await response.text()

            if response.status != 200:
                raise RuntimeError(
                    f"OpenAI API error {response.status}: {response_text[:500]}"
                )

            data = json.loads(response_text)

    result_text = ""

    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                result_text += content.get("text", "")

    if not result_text:
        raise RuntimeError("OpenAI returned an empty response")

    result_text = result_text.strip()

    # На случай если модель обернула JSON в ```json ... ```
    if result_text.startswith("```"):
        result_text = result_text.replace("```json", "", 1)
        result_text = result_text.replace("```", "")
        result_text = result_text.strip()

    result = json.loads(result_text)

    min_kg = float(result["min_kg"])
    max_kg = float(result["max_kg"])

    if min_kg <= 0 or max_kg <= 0:
        raise ValueError("Invalid weight returned by AI")

    if max_kg < min_kg:
        min_kg, max_kg = max_kg, min_kg

    confidence = result.get("confidence", "low")

    if confidence not in ("low", "medium", "high"):
        confidence = "low"

    return {
        "product_type": result.get("product_type", "Товар"),
        "min_kg": round(min_kg, 3),
        "max_kg": round(max_kg, 3),
        "confidence": confidence,
        "note": result.get(
            "note",
            "Вес определён приблизительно по фотографии."
        ),
    }
