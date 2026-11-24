from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False,
    device="cpu"
)


def extract_text(image_path):

    results = ocr.predict(image_path)

    extracted_data = []

    for result in results:
        data = result.json["res"]

        texts = data.get("rec_texts", [])
        scores = data.get("rec_scores", [])
        boxes = data.get("rec_boxes", [])

        for text, score, box in zip(texts, scores, boxes):

            extracted_data.append({
                "text": text,
                "confidence": float(score),
                "bounding_box": box.tolist()
                if hasattr(box, "tolist") else box
            })

    return extracted_data