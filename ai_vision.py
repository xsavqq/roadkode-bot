import base64
import json
import os

import aiohttp


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")


async def estimate_weight_from_image(image_bytes: bytes) -> dict:
    """
    Оценивает примерный вес товара по фотографии.

    ВАЖНО:
    AI-вес используется только как ориентир.
    Он НЕ используется для расчёта доставки.

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
        raise RuntimeError(
            "OPENAI_API_KEY is not configured"
        )

    if not image_bytes:
        raise ValueError(
            "Image is empty"
        )

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    prompt = """
Ты анализируешь фотографию товара для интернет-магазина.

Твоя задача — определить тип товара и ОЦЕНИТЬ его примерный
вес без упаковки.

КРИТИЧЕСКИ ВАЖНО:

1. Это только приблизительная оценка по фотографии.
2. Нельзя выдавать ложную точность.
3. Всегда указывай ДИАПАЗОН веса.
4. Если определить вес сложно — делай диапазон шире.
5. Вес указывай БЕЗ упаковки.
6. Если на фото несколько одинаковых товаров — оцени вес ОДНОЙ штуки.
7. Учитывай:
   - тип товара;
   - материал;
   - примерный размер;
   - конструкцию;
   - толщину;
   - наличие металлических деталей;
   - визуальную плотность материала.
8. Не учитывай стоимость товара.
9. Не пытайся определить вес по цене.
10. Не используй упаковку в оценке.
11. Не придумывай точные характеристики, которых не видно.
12. Если масштаб фотографии неизвестен, учитывай это и расширяй диапазон.
13. Ответ должен быть ТОЛЬКО JSON без Markdown и без ```.

Формат:

{
  "product_type": "краткое название товара",
  "min_kg": 0.2,
  "max_kg": 0.5,
  "confidence": "low",
  "note": "краткое объяснение оценки на русском языке"
}

Правила для confidence:

"high" — товар хорошо виден, его тип и примерный размер понятны.

"medium" — товар понятен, но есть неопределённость с размером,
материалом или конструкцией.

"low" — по фотографии сложно надёжно определить вес.

Правила для веса:

- min_kg > 0
- max_kg > 0
- max_kg >= min_kg
- используй килограммы
- не указывай заведомо сверхточный диапазон
  вроде 0.437–0.451 кг
- диапазон должен соответствовать реальной неопределённости
  оценки

Например, лучше:
0.4–0.7 кг

чем:
0.53–0.56 кг

если точный размер и материал неизвестны.
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
                            "data:image/jpeg;base64,"
                            f"{image_base64}"
                        ),
                        "detail": "low",
                    },
                ],
            }
        ],
    }

    timeout = aiohttp.ClientTimeout(
        total=45
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        async with session.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": (
                    f"Bearer {OPENAI_API_KEY}"
                ),
                "Content-Type": "application/json",
            },
            json=payload,
        ) as response:

            response_text = await response.text()

            if response.status != 200:
                raise RuntimeError(
                    "OpenAI API error "
                    f"{response.status}: "
                    f"{response_text[:500]}"
                )

            try:
                data = json.loads(
                    response_text
                )
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    "OpenAI returned invalid JSON response"
                ) from e

    # -----------------------------------------------------
    # Достаём текст из Responses API
    # -----------------------------------------------------

    result_text = ""

    for output in data.get(
        "output",
        []
    ):
        for content in output.get(
            "content",
            []
        ):
            if content.get(
                "type"
            ) == "output_text":

                result_text += (
                    content.get(
                        "text",
                        ""
                    )
                )

    if not result_text:
        raise RuntimeError(
            "OpenAI returned an empty response"
        )

    result_text = result_text.strip()

    # -----------------------------------------------------
    # Убираем Markdown, если модель всё-таки
    # вернула ```json ... ```
    # -----------------------------------------------------

    if result_text.startswith("```"):

        if result_text.startswith(
            "```json"
        ):
            result_text = result_text[
                len("```json"):
            ]
        else:
            result_text = result_text[
                len("```"):
            ]

        if result_text.endswith(
            "```"
        ):
            result_text = result_text[
                :-3
            ]

        result_text = result_text.strip()

    # -----------------------------------------------------
    # Иногда модель может вернуть текст до/после JSON.
    # Пытаемся найти объект JSON.
    # -----------------------------------------------------

    if not (
        result_text.startswith("{")
        and result_text.endswith("}")
    ):
        start = result_text.find("{")
        end = result_text.rfind("}")

        if start != -1 and end != -1:
            result_text = result_text[
                start:end + 1
            ]

    try:
        result = json.loads(
            result_text
        )
    except json.JSONDecodeError as e:
        raise RuntimeError(
            "AI returned invalid JSON: "
            f"{result_text[:500]}"
        ) from e

    # -----------------------------------------------------
    # Проверяем вес
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
        ValueError
    ) as e:
        raise ValueError(
            "AI returned invalid weight values"
        ) from e

    if min_kg <= 0 or max_kg <= 0:
        raise ValueError(
            "Invalid weight returned by AI"
        )

    if max_kg < min_kg:
        min_kg, max_kg = (
            max_kg,
            min_kg
        )

    # -----------------------------------------------------
    # Защита от совсем нереалистичных значений
    # -----------------------------------------------------

    if min_kg > 500 or max_kg > 500:
        raise ValueError(
            "AI returned unrealistic weight"
        )

    # -----------------------------------------------------
    # Нормализуем confidence
    # -----------------------------------------------------

    confidence = result.get(
        "confidence",
        "low"
    )

    if confidence not in (
        "low",
        "medium",
        "high",
    ):
        confidence = "low"

    product_type = result.get(
        "product_type",
        "Товар"
    )

    note = result.get(
        "note",
        "Вес определён приблизительно "
        "по фотографии."
    )

    # -----------------------------------------------------
    # Финальный результат
    # -----------------------------------------------------

    return {
        "product_type": str(
            product_type
        )[:100],

        "min_kg": round(
            min_kg,
            3
        ),

        "max_kg": round(
            max_kg,
            3
        ),

        "confidence": confidence,

        "note": str(
            note
        )[:300],
    }
