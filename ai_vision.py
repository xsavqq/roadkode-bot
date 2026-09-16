import base64
import json
import re

import aiohttp

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
)


# =========================================================
# AI ОЦЕНКА ВЕСА
# =========================================================

async def estimate_weight_from_image(
    image_bytes: bytes,
) -> dict:

    """
    Анализирует фотографию товара
    и возвращает приблизительный диапазон веса.
    """

    if not OPENAI_API_KEY:

        raise RuntimeError(
            "OPENAI_API_KEY is not configured"
        )

    if not image_bytes:

        raise ValueError(
            "Image is empty"
        )

    # -----------------------------------------------------
    # КАРТИНКА → BASE64
    # -----------------------------------------------------

    image_base64 = (
        base64.b64encode(
            image_bytes
        ).decode("ascii")
    )

    data_url = (
        "data:image/jpeg;base64,"
        + image_base64
    )

    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    prompt = """

Проанализируй фотографию товара и оцени
его примерный вес БЕЗ упаковки.

ВАЖНЫЕ ПРАВИЛА:

- Это только приблизительная оценка.
- Никогда не выдавай ложную точность.
- Всегда указывай диапазон веса.
- Если определить вес сложно — делай диапазон шире.
- Если на фото несколько одинаковых товаров —
  оцени вес ОДНОЙ штуки.
- Учитывай тип товара.
- Учитывай материал, если он визуально понятен.
- Учитывай примерный размер и конструкцию.
- Если масштаб фотографии неизвестен —
  учитывай эту неопределённость.
- Не учитывай упаковку.
- Не пытайся определить вес по цене.
- Не придумывай характеристики,
  которых не видно на фотографии.
- Не используй псевдоточность.
- Ответ должен быть ТОЛЬКО JSON.
- Не добавляй markdown.

Формат ответа:

{
  "product_type": "краткое название товара",
  "min_kg": 0.2,
  "max_kg": 0.5,
  "confidence": "low",
  "note": "краткое объяснение на русском"
}

confidence:
только low, medium или high.

min_kg:
положительное число.

max_kg:
положительное число,
не меньше min_kg.

Если информации мало,
лучше дать широкий диапазон,
чем делать вид, что вес известен точно.
"""

    # -----------------------------------------------------
    # OPENAI REQUEST
    # -----------------------------------------------------

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

                        "image_url": data_url,

                        "detail": "low",
                    },
                ],
            }
        ],
    }

    timeout = aiohttp.ClientTimeout(
        total=45
    )

    # -----------------------------------------------------
    # ЗАПРОС
    # -----------------------------------------------------

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        async with session.post(

            "https://api.openai.com/v1/responses",

            headers={

                "Authorization":
                    f"Bearer {OPENAI_API_KEY}",

                "Content-Type":
                    "application/json",
            },

            json=payload,

        ) as response:

            response_text = (
                await response.text()
            )

            if response.status != 200:

                raise RuntimeError(

                    "OpenAI API error "
                    f"{response.status}: "
                    f"{response_text[:500]}"
                )

            try:

                api_data = json.loads(
                    response_text
                )

            except json.JSONDecodeError as exc:

                raise RuntimeError(
                    "OpenAI returned invalid JSON"
                ) from exc

    # -----------------------------------------------------
    # ДОСТАЁМ ТЕКСТ
    # -----------------------------------------------------

    result_text = ""

    for output in api_data.get(
        "output",
        [],
    ):

        for content in output.get(
            "content",
            [],
        ):

            if (
                content.get("type")
                == "output_text"
            ):

                result_text += (
                    content.get(
                        "text",
                        "",
                    )
                )

    result_text = (
        result_text.strip()
    )

    if not result_text:

        raise RuntimeError(
            "OpenAI returned an empty response"
        )

    # -----------------------------------------------------
    # УБИРАЕМ ```JSON
    # -----------------------------------------------------

    result_text = re.sub(

        r"^```(?:json)?\s*",

        "",

        result_text,
    ).strip()

    result_text = re.sub(

        r"\s*```$",

        "",

        result_text,
    ).strip()

    # -----------------------------------------------------
    # ЕСЛИ AI ДОБАВИЛ ТЕКСТ
    # -----------------------------------------------------

    if not result_text.startswith(
        "{"
    ):

        start = (
            result_text.find("{")
        )

        end = (
            result_text.rfind("}")
        )

        if (
            start != -1
            and end != -1
        ):

            result_text = (
                result_text[
                    start:end + 1
                ]
            )

    # -----------------------------------------------------
    # JSON
    # -----------------------------------------------------

    try:

        result = json.loads(
            result_text
        )

    except json.JSONDecodeError as exc:

        raise RuntimeError(

            "AI returned invalid JSON: "
            f"{result_text[:500]}"

        ) from exc

    # -----------------------------------------------------
    # ВЕС
    # -----------------------------------------------------

    try:

        min_kg = float(
            result["min_kg"]
        )

        max_kg = float(
            result["max_kg"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            "AI returned invalid weight values"
        ) from exc

    if (
        min_kg <= 0
        or max_kg <= 0
    ):

        raise ValueError(
            "AI returned invalid weight range"
        )

    if max_kg < min_kg:

        min_kg, max_kg = (
            max_kg,
            min_kg,
        )

    # -----------------------------------------------------
    # ЗАЩИТА ОТ БРЕДА
    # -----------------------------------------------------

    if max_kg > 500:

        raise ValueError(
            "AI returned unrealistic weight"
        )

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    confidence = result.get(
        "confidence",
        "low",
    )

    if confidence not in (
        "low",
        "medium",
        "high",
    ):

        confidence = "low"

    # -----------------------------------------------------
    # РЕЗУЛЬТАТ
    # -----------------------------------------------------

    return {

        "product_type": str(
            result.get(
                "product_type"
            )
            or "Товар"
        )[:100],

        "min_kg": round(
            min_kg,
            2,
        ),

        "max_kg": round(
            max_kg,
            2,
        ),

        "confidence": confidence,

        "note": str(

            result.get(
                "note"
            )
            or
            "Вес определён "
            "приблизительно "
            "по фотографии."

        )[:300],
    }
