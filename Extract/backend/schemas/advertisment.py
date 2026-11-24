
from pydantic import BaseModel, Field
from typing import Optional





class AdvertisementSchema(BaseModel):

    # Advertisement classification
    ad_category: Optional[str] = Field(
        default=None,
        description=(
            "Industry or category of the advertisement, such as "
            "automobile, real estate, education, jewellery, "
            "electronics, retail, healthcare, food or services."
        )
    )

    ad_type: str|None = Field(
        default=None,
        description=(
            "Type or format of advertisement, such as dealer, "
            "retail, promotional, classified, recruitment, "
            "institutional or brand advertisement. "
            "Extract based on the advertisement."
        )
    )

    
    client: list[str] = Field(
        default_factory=list,
        description=(
            "Names of clients, advertisers, dealers, distributors, "
            "institutions or businesses placing or promoting "
            "the advertisement. Extract all explicitly identified "
            "clients without confusing them with product brands."
        )
    )

    brand:str|None = Field(
        default=None,
        description=(
            "Actual brand, manufacturer, company or institution "
            "whose product or service is advertised."
        )
    )

    
    headline: Optional[str] = Field(
        default=None,
        description=(
            "Main promotional headline or slogan. "
            "Preserve original wording."
        )
    )

    description:str|None = Field(
        default=None,
        description=(
            "Main descriptive text or body copy explaining "
            "the advertised products, services, benefits or "
            "organization. Preserve relevant information and "
            "do not confuse it with the headline."
        )
    )

    product_name: str = Field(
            description=(
                "Exact name of the product, service, property, "
                "course, or offering extracted from the advertisement. "
                "Use OCR text and the original image. Do not guess."
            )
        )
    
    product_specification: dict[str, str] = Field(
            default_factory=dict,
            description=(
                "Specifications and features belonging specifically "
                "to this product. Use category-relevant key-value pairs. "
                "Do not invent missing information."
            )
        )
    
    
    
    price: Optional[str] = Field(
        default=None,
        description=(
            "General advertisement-level price, starting price, "
            "price range or fee that cannot be associated with "
            "a particular product. Preserve currency and conditions."
        )
    )

    
    offer: list[str] = Field(
        default_factory=list,
        description=(
            "Promotional offers, discounts, cashback, exchange "
            "offers, free gifts, financing benefits and other "
            "advertised promotional conditions."
        )
    )

    
    contact: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Contact details using keys such as phone, email, "
            "website, dealer, showroom, sales_person or "
            "customer_support. Values must be lists of strings."
        )
    )

    
    location: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Explicit geographical or business locations using "
            "keys such as address, city, state, country, pincode, "
            "branch or service_area."
        )
    )

    
    missing_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Relevant and applicable information fields that "
            "could not be found or extracted. Exclude irrelevant "
            "fields. Use exact schema field names."
        )
    )

    uncertain_fields: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Fields with ambiguous, partially readable, conflicting "
            "or uncertain information. Map field names to a short "
            "explanation. Never guess uncertain values."
        )
    )
