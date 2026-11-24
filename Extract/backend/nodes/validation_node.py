
import json

from pydantic import ValidationError

from Extract.backend.schemas.advertisment import AdvertisementSchema



def validation_node(state):

    try:
        # Step 1: Validate Nemotron JSON using Pydantic
        record = AdvertisementSchema.model_validate_json(
            state["raw_output"]
        )

        

        # Step 5: Convert Pydantic model into dictionary
        clean_output = record.model_dump()

        return {
            "validated_data": clean_output,
            "errors": []
        }

    except ValidationError as e:

        return {
            "validated_data": None,
            "errors": [str(e)]
        }

    