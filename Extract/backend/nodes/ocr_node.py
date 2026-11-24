from Extract.peddleOCR import extract_text

def ocr_node(state):

    image_path = state["image_path"]

    
    ocr_results = extract_text(str(image_path))

    # Convert OCR results into readable text
    ocr_text = "\n".join(
        [
            f"- {item['text']} (confidence: {item['confidence']:.2f})"
            for item in ocr_results
        ]
    )

    return {
        "ocr_results": ocr_results,
        "ocr_text": ocr_text
    }
