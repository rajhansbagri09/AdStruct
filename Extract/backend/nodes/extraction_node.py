
import os
import base64
import mimetypes
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA

from Extract.backend.schemas.advertisment import AdvertisementSchema

load_dotenv()

MODEL_NAME = "nvidia/nemotron-3.5-super-vl-120b-a12b"

if not os.getenv("NVIDIA_API_KEY"):
    raise ValueError("NVIDIA_API_KEY not found in environment variables")

client = ChatNVIDIA(
    base_url="https://integrate.api.nvidia.com/v1",
    model=MODEL_NAME,
    api_key=os.getenv("NVIDIA_API_KEY"),
    temperature=0.1,
    top_p=0.95,
    max_completion_tokens=8192,
    seed=42,
)

client = client.bind(
    chat_template_kwargs={"enable_thinking": False}
)


def extraction_node(state):

    image_path = state["image_path"]
    ocr_text = state["ocr_text"]

    # Extraction prompt
    prompt = f"""You are an advanced, evidence-based advertisement information extraction system designed to convert advertisement images into accurate, structured data.

    Your task is to understand the complete advertisement and extract its information according to the exact output schema.

    ## INPUT SOURCES

    You will receive:

    1. **Original advertisement image:** The primary source of truth. Analyze its complete visual content, including headings, text, tables, product images, logos, labels, price sections, disclaimers, and contact information.
    2. **PaddleOCR text:** A supporting source that may contain recognition errors, missing words, incorrect characters, duplicated text, or incorrect reading order.

    Use both sources together. Do not treat OCR output as completely accurate.

    ## CORE EXTRACTION PRINCIPLES

    1. Extract information only when supported by visible evidence in the image or OCR text.
    2. Never invent, assume, infer unsupported details, or use external knowledge.
    3. The original image takes priority over OCR whenever they disagree.
    4. Use OCR to help identify small or difficult text, but verify it against the image whenever possible.
    5. Preserve the original spelling, capitalization, language, numbers, symbols, units, and currency.
    6. Do not translate, paraphrase, improve, or rewrite advertisement content.
    7. Do not convert partially visible information into a complete value.
    8. Do not confuse product names, model numbers, phone numbers, dates, prices, addresses, and specifications.
    9. Extract all distinct relevant information, but do not duplicate the same information across fields.
    10. Do not force information into a field when its meaning is unclear.

    ## FIELD EXTRACTION INSTRUCTIONS

    ### 1. ad_category
    Identify the industry or business category of the advertisement.

    Examples:
    - automobile
    - real_estate
    - education
    - jewellery
    - electronics
    - retail
    - healthcare
    - food_beverage
    - fashion
    - finance
    - travel
    - recruitment
    - services

    Choose the category based on the actual offering, not merely the advertiser's business name. Return null if it cannot be determined.

    ### 2. ad_type
    Identify the advertisement's format or commercial purpose.

    Examples:
    - dealer
    - retail
    - promotional
    - classified
    - recruitment
    - institutional
    - brand

    Use the most appropriate value supported by the advertisement. Do not confuse the advertisement type with its industry category. Return null if unclear.

    ### 3. client
    Extract the names of advertisers, dealers, distributors, agencies, institutions, or businesses explicitly associated with placing or promoting the advertisement.

    Rules:
    - Return a list of strings.
    - Include multiple clients when explicitly shown.
    - A dealer or showroom may be a client.
    - Do not automatically treat the manufacturer or product brand as the client.
    - Do not add a company merely because its logo or product appears in the advertisement.

    ### 4. brand
    Extract the actual brand, manufacturer, company, or institution whose product or service is being advertised.

    Rules:
    - Keep the brand separate from the dealer, distributor, agency, or client.
    - Do not mistake a dealership name for the manufacturer's brand.
    - If multiple brands are advertised, include the clearly identifiable primary brand only. Do not combine unrelated brands into one value.
    - Return null when the brand cannot be established from visible evidence.

    ### 5. headline
    Extract the primary headline, slogan, or promotional heading exactly as displayed.

    Rules:
    - Preserve original wording and punctuation.
    - Do not use the brand name or product name as the headline unless it is explicitly presented as the main heading.
    - Do not include the complete body description here.
    - Return null if no headline is present.

    ### 6. description
    Extract the main descriptive text explaining the advertised offering.

    Rules:
    - Preserve the original wording and language.
    - Include relevant descriptive statements and supporting promotional text.
    - Do not repeat the headline.
    - Do not move product-specific technical specifications, prices, offers, or contact information into this field when they have dedicated fields.
    - Do not create a description if the advertisement contains no meaningful body text; return null instead.

    ### 7. product_name
    Extract the exact name of the primary product, service, property, course, or offering explicitly advertised.

    Rules:
    - Return a single string containing the exact product or offering name as displayed.
    - Include model names or variants only when explicitly visible.
    - If multiple distinct products are shown, extract the primary advertised product name (or comma-separated names only if they share a single unified listing).
    - Do not create a product name from a feature, slogan, specification, or brand name alone.
    - Return "" (empty string) if no identifiable product or offering is present.

    ### 8. product_specification
    Extract objective attributes, technical specifications, configurations, or core service/program offerings belonging specifically to the advertised product or service into a dictionary of string key-value pairs.

    Rules:

    -Universal Scope: Capture factual characteristics that define the product or service itself across any category—such as physical specs, dimensions, capacity, configurations, certifications, affiliations, or specific programs/services offered (e.g., ram, mileage, area, purity, affiliations, courses_offered, duration, course_mode).

    -One Concept per Key: Use clear, snake_case attribute names. If an ad lists multiple distinct sub-offerings of the same type (e.g., multiple courses, variants, or amenities), group them cleanly under a single descriptive plural key (e.g., "courses_offered": "B.Pharma, B.Com, B.Ed.") rather than cluttering the dictionary with numbered keys.

    -Exact Preservation: Preserve the displayed value, unit, and wording exactly as shown in the ad.

    -Strict Exclusions: Do not include prices, EMI/financial terms, promotional offers/discounts, contact details, locations, or subjective marketing claims (e.g., "Best in class", "Excellent placement").

    -Zero Inference: Do not invent, normalize, or add specifications based on external product knowledge.

    -Empty Fallback: Return {{}} if no objective specifications or core offerings are present.

    ### 9. price
    Extract the advertisement's price, starting price, fee, or price range.

    Rules:
    - Preserve the original currency, amount, units, and pricing conditions.
    - Examples: "Starting from ₹...", "Admission fee ₹...", "₹... per month", "₹49,999".
    - Never treat phone numbers, dates, model numbers, registration numbers, or other numeric identifiers as prices.
    - Return null if no price is displayed.

    ### 10. offer
    Extract explicitly advertised promotional benefits and commercial deals.

    Examples:
    - Discounts
    - Cashback
    - Exchange bonuses
    - Free gifts
    - EMI offers
    - Limited-period deals
    - Special benefits

    Rules:
    - Return a list of strings.
    - Preserve offer conditions, amounts, percentages, and validity periods when shown.
    - Do not convert ordinary product features into offers.
    - Do not invent eligibility conditions or promotional benefits.

    ### 11. contact
    Extract contact information into a dictionary where every value is a list of strings.

    Allowed keys:
    - phone
    - email
    - website
    - dealer
    - showroom
    - sales_person
    - customer_support

    Rules:
    - Preserve phone numbers exactly, including country codes and visible formatting.
    - Do not complete incomplete or partially visible phone numbers.
    - Remove exact duplicate entries within the same contact category.
    - Do not place physical addresses in contact.
    - Do not classify a phone number as a website, or vice versa.
    - Include a contact person or dealership name only when explicitly associated with contact information.

    ### 12. location
    Extract explicitly displayed geographical information into a dictionary of string values.

    Allowed keys:
    - address
    - city
    - state
    - country
    - pincode
    - branch
    - service_area

    Rules:
    - Preserve the displayed location wording.
    - Separate city, state, country, and pincode only when identifiable.
    - Do not derive a city or state from a phone code, brand name, or outside knowledge.
    - Do not confuse a dealer name with a location.
    - Do not place phone numbers or other contact details here.
    - Include only locations explicitly supported by the advertisement.

    ### 13. missing_fields
    Identify relevant schema fields that should contain information for this advertisement but were not found.

    Rules:
    - Return a list of exact schema field names (e.g., "price", "contact", "location", "product_specification").
    - Include only fields relevant to the advertised content.
    - Do not mark optional or irrelevant information as missing merely because it is absent.
    - A field containing null, "", an empty list, or an empty dictionary may be reported as missing when it is relevant.
    - Do not report a field as missing if it contains usable extracted information.

    ### 14. uncertain_fields
    Identify information that appears in the advertisement but cannot be extracted confidently because it is blurry, partially visible, ambiguous, or conflicting.

    Rules:
    - Return a dictionary containing exact schema field paths as keys and short explanations as values, such as:
    - "brand"
    - "product_name"
    - "product_specification.mileage"
    - "contact.phone"
    - "location.address"
    - Explain the specific uncertainty briefly.
    - Do not guess or silently correct uncertain information.
    - Do not mark completely absent information as uncertain; use missing_fields instead.
    - If the value is clear and reliable, do not mark it uncertain.

    ## OUTPUT VALIDATION RULES

    Before returning the result, verify that:

    1. All 14 required top-level keys are present.
    2. Every key has the exact required data type:
    - `ad_category`, `ad_type`, `brand`, `headline`, `description`, `price`: string or null
    - `product_name`: string (use "" if missing, since it is non-optional in the schema)
    - `client`, `offer`, `missing_fields`: list of strings
    - `product_specification`, `location`, `uncertain_fields`: dictionary of string keys to string values
    - `contact`: dictionary of string keys to list of strings
    3. No unsupported or additional fields (such as a `products` list) are included.
    4. No information is duplicated unnecessarily.
    5. No unsupported values have been invented.

    For missing values, use:
    - `null` for missing optional scalar values (`ad_category`, `ad_type`, `brand`, `headline`, `description`, `price`).
    - `""` for missing `product_name`.
    - `[]` for missing lists (`client`, `offer`, `missing_fields`).
    - `{{}}` for missing dictionaries (`product_specification`, `contact`, `location`, `uncertain_fields`).

    ## OUTPUT FORMAT

    Return ONLY one valid JSON object.

    Use exactly these top-level keys:

    ad_category, ad_type, client, brand, headline, description, product_name, product_specification, price, offer, contact, location, missing_fields, uncertain_fields.

    Do not return explanations, markdown, comments, confidence scores, or code fences.

    ## OCR TEXT

    {ocr_text}
    """


    

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Advertisement image not found: {image_path}"
        )

    mime_type, _ = mimetypes.guess_type(str(image_path))

    if mime_type is None:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(
            image_file.read()
        ).decode("utf-8")

    image_url = f"data:{mime_type};base64,{image_base64}"

    # Send original image +  extraction prompt

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            }
        ]
    )

    

    response = client.invoke([message])

    raw_output = response.content

    

    if isinstance(raw_output, list):
        raw_output = "".join(
            block.get("text", "")
            for block in raw_output
            if isinstance(block, dict)
        )

    if not isinstance(raw_output, str) or not raw_output.strip():
        raise ValueError("NVIDIA returned an empty model response")

    return {
        "raw_output": raw_output
    }