
from typing import TypedDict, Any


class AdvertisementState(TypedDict, total=False):

    image_path: str
    ocr_results: Any
    ocr_text: str
    raw_output: str
    validated_data: dict | None
    errors: list[str]
