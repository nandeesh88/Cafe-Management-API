import anthropic
import base64
import os
from pathlib import Path


def identify_item_from_image(image_path: str, media_type: str = "image/jpeg") -> dict:
    """
    Send an image to Claude and identify what café inventory item it contains.
    Returns dict with 'item_name' and 'confidence_note'.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Fast and free-tier friendly
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are an AI assistant for a café inventory system. "
                            "Look at this image and identify the café-related item shown. "
                            "Respond ONLY in this exact JSON format with no extra text:\n"
                            '{"item_name": "<short item name, e.g. Arabica Coffee Beans>", '
                            '"confidence_note": "<one sentence about your confidence>"}'
                        ),
                    },
                ],
            }
        ],
    )

    import json
    raw = message.content[0].text.strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract best guess
        result = {
            "item_name": "Unknown Item",
            "confidence_note": f"Could not parse AI response: {raw[:100]}"
        }

    result["raw_response"] = raw
    return result
