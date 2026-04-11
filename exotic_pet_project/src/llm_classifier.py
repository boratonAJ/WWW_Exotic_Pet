import os
from typing import Iterable

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Classify exotic pet trade discussion text into exactly one category:

- Legal Risk
- Safety Risk
- Animal Welfare
- Conservation
- Trade/Sales
- Neutral

Return only the category name.
""".strip()


def classify_themes_llm(
    texts: Iterable[str],
    model: str = "gpt-4o-mini",
):
    labels = []
    errors = []

    for text in texts:
        try:
            text = str(text).strip()

            if not text:
                labels.append("Neutral")
                errors.append("")
                continue

            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text[:1500]},
                ],
            )

            label = response.choices[0].message.content
            label = label.strip() if label else "Neutral"

            labels.append(label)
            errors.append("")

        except Exception as e:
            labels.append("LLM_Error")
            errors.append(f"{type(e).__name__}: {e}")

    return labels, errors