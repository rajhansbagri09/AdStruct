import os
import sys

os.environ["PADDLE_PDX_EAGER_INIT"] = "False"

print("PaddleX eager init:", os.environ.get("PADDLE_PDX_EAGER_INIT"))
print("PaddleX already imported:", "paddlex" in sys.modules)


import sys
import json
import uuid
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv


# =====================================================
# 1. PROJECT CONFIGURATION
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

UPLOAD_DIR = PROJECT_ROOT / "outputs" / "uploads"
APPROVED_DIR = PROJECT_ROOT / "outputs" / "approved"
REJECTED_DIR = PROJECT_ROOT / "outputs" / "rejected"

for folder in [UPLOAD_DIR, APPROVED_DIR, REJECTED_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


# =====================================================
# 2. BACKEND IMPORTS
# =====================================================

from Extract.backend.graph.workflow import advertisement_workflow
from Extract.backend.schemas.advertisment import AdvertisementSchema


# =====================================================
# 3. PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="AdStruct AI",
    
    layout="wide"
)

st.title("AdStruct AI 📄")
st.caption("AI-Powered Advertisement Data Extraction & Structuring System with human verification")


# =====================================================
# 4. SESSION STATE
# =====================================================

DEFAULT_STATE = {
    "extracted_data": None,
    "image_path": None,
    "run_id": None,
    "approved_json": None,
    "approved_path": None,
    "approved_excel_path": None,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clear_extraction():
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value


# =====================================================
# 5. HELPER FUNCTIONS
# =====================================================

def text_value(value):
    """Convert optional values into safe text."""
    if value is None:
        return ""
    return str(value)


def list_to_text(value):
    """Convert a list into editable multiline text."""
    if not isinstance(value, list):
        return text_value(value)

    return "\n".join(str(item) for item in value if item is not None)


def text_to_list(value):
    """Convert multiline text into a list."""
    return [
        line.strip()
        for line in value.splitlines()
        if line.strip()
    ]


def dict_to_rows(data):
    """Convert a dictionary into editable table rows."""
    if not isinstance(data, dict):
        return []

    return [
        {"Field": key, "Value": value}
        for key, value in data.items()
    ]


def contact_to_rows(data):
    """Convert contact dictionary into editable rows."""
    rows = []

    if not isinstance(data, dict):
        return rows

    for contact_type, values in data.items():
        if not isinstance(values, list):
            values = [values]

        for value in values:
            if value is not None:
                rows.append({
                    "Contact Type": contact_type,
                    "Value": value
                })

    return rows


def clean_cell(value):
    """Safely handle blank and NaN table cells."""
    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def rows_to_dict(df, key_column="Field", value_column="Value"):
    result = {}

    for _, row in df.iterrows():
        key = clean_cell(row.get(key_column))
        value = clean_cell(row.get(value_column))

        if key and value:
            result[key] = value

    return result


def rows_to_contact(df):
    result = {}

    for _, row in df.iterrows():
        contact_type = clean_cell(row.get("Contact Type"))
        value = clean_cell(row.get("Value"))

        if contact_type and value:
            result.setdefault(contact_type, [])

            if value not in result[contact_type]:
                result[contact_type].append(value)

    return result



def create_excel_workbook(data):
    """Create a structured multi-sheet Excel workbook from approved data."""

    excel_buffer = BytesIO()

    advertisement_rows = [
        {"Field": "Ad Category", "Value": data.get("ad_category") or ""},
        {"Field": "Ad Type", "Value": data.get("ad_type") or ""},
        {"Field": "Brand", "Value": data.get("brand") or ""},
        {"Field": "Headline", "Value": data.get("headline") or ""},
        {"Field": "Description", "Value": data.get("description") or ""},
        {"Field": "Product Name", "Value": data.get("product_name") or ""},
        {"Field": "Price", "Value": data.get("price") or ""},
    ]

    specification_rows = [
        {"Specification": key, "Value": value}
        for key, value in (data.get("product_specification") or {}).items()
    ]

    client_offer_rows = (
        [{"Type": "Client", "Value": value} for value in data.get("client", [])]
        + [{"Type": "Offer", "Value": value} for value in data.get("offer", [])]
    )

    contact_rows = [
        {"Contact Type": contact_type, "Value": value}
        for contact_type, values in (data.get("contact") or {}).items()
        for value in (values if isinstance(values, list) else [values])
    ]

    location_rows = [
        {"Location Field": key, "Value": value}
        for key, value in (data.get("location") or {}).items()
    ]

    review_rows = [
        {"Note Type": "Missing Field", "Field": field, "Details": ""}
        for field in data.get("missing_fields", [])
    ] + [
        {"Note Type": "Uncertain Field", "Field": field, "Details": reason}
        for field, reason in (data.get("uncertain_fields") or {}).items()
    ]

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        pd.DataFrame(advertisement_rows).to_excel(
            writer, sheet_name="Advertisement Details", index=False
        )
        pd.DataFrame(
            specification_rows, columns=["Specification", "Value"]
        ).to_excel(writer, sheet_name="Product Specifications", index=False)
        pd.DataFrame(
            client_offer_rows, columns=["Type", "Value"]
        ).to_excel(writer, sheet_name="Clients & Offers", index=False)
        pd.DataFrame(
            contact_rows, columns=["Contact Type", "Value"]
        ).to_excel(writer, sheet_name="Contact Details", index=False)
        pd.DataFrame(
            location_rows, columns=["Location Field", "Value"]
        ).to_excel(writer, sheet_name="Location", index=False)
        pd.DataFrame(
            review_rows, columns=["Note Type", "Field", "Details"]
        ).to_excel(writer, sheet_name="Review Notes", index=False)

    return excel_buffer.getvalue()


# =====================================================
# 6. IMAGE UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "Upload Advertisement Image",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:

    st.caption(f"Selected file: {uploaded_file.name}")

    if st.button("Extract Advertisement", type="primary"):

        clear_extraction()

        filename = f"{uuid.uuid4().hex}_{Path(uploaded_file.name).name}"
        image_path = UPLOAD_DIR / filename

        image_path.write_bytes(uploaded_file.getvalue())

        st.session_state.image_path = str(image_path)

        with st.spinner("Extracting advertisement information..."):

            try:
                result = advertisement_workflow.invoke({
                    "image_path": str(image_path),
                    "errors": []
                })
                print("\n========== WORKFLOW VALIDATED DATA ==========")
                print(result.get("validated_data"))

                print("\n========== INDIVIDUAL FIELDS ==========")

                for field in [
                    "ad_category",
                    "ad_type",
                    "client",
                    "brand",
                    "headline",
                    "description"
                ]:
                    print(field, ":", result.get("validated_data", {}).get(field))

                if result.get("errors"):
                    st.error("Extraction failed.")

                    for error in result["errors"]:
                        st.error(error)

                elif result.get("validated_data") is not None:

                    st.session_state.extracted_data = result["validated_data"]
                    st.session_state.run_id = uuid.uuid4().hex

                    st.rerun()

                else:
                    st.error("No validated data returned by the workflow.")

            except Exception as error:
                st.error(f"Pipeline error: {error}")


# =====================================================
# 7. IMAGE PREVIEW + EDITABLE FORM
# =====================================================

if st.session_state.extracted_data is not None:

    data = st.session_state.extracted_data
    run_id = st.session_state.run_id

    st.divider()
    st.subheader("Advertisement Review")

    preview_col, form_col = st.columns(
        [1, 1.4],
        gap="large"
    )

    # -------------------------------------------------
    # LEFT: ORIGINAL IMAGE
    # -------------------------------------------------

    with preview_col:

        st.markdown("### Original Advertisement")

        image_path = st.session_state.image_path

        if image_path and Path(image_path).exists():
            st.image(
                image_path,
                use_container_width=True
            )

        # Approval status and download

        if st.session_state.approved_json is not None:

            st.success("Advertisement approved successfully.")

            st.download_button(
                "Download Approved Record",
                data=json.dumps(
                    st.session_state.approved_json,
                    ensure_ascii=False,
                    indent=4
                ),
                file_name=Path(
                    st.session_state.approved_path
                ).name,
                mime="application/json",
                use_container_width=True
            )

            st.download_button(
                "Download Excel Workbook",
                data=Path(st.session_state.approved_excel_path).read_bytes(),
                file_name=Path(st.session_state.approved_excel_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.divider()

        if st.button(
            "Reject Advertisement",
            use_container_width=True
        ):

            if image_path:
                source = Path(image_path)

                if source.exists():
                    destination = REJECTED_DIR / source.name
                    source.replace(destination)

            clear_extraction()
            st.rerun()


    # -------------------------------------------------
    # RIGHT: EDITABLE FORM
    # -------------------------------------------------

    with form_col:

        with st.form(key=f"review_{run_id}"):

            # 1. Advertisement details

            st.markdown("### Advertisement Details")

            col1, col2 = st.columns(2)

            with col1:

                ad_category = st.text_input(
                    "Ad Category",
                    value=text_value(data.get("ad_category"))
                )

                brand = st.text_input(
                    "Brand",
                    value=text_value(data.get("brand"))
                )

                headline = st.text_input(
                    "Headline",
                    value=text_value(data.get("headline"))
                )

            with col2:

                ad_type = st.text_input(
                    "Ad Type",
                    value=text_value(data.get("ad_type"))
                )

                price = st.text_input(
                    "Price",
                    value=text_value(data.get("price"))
                )

                product_name = st.text_input(
                    "Product Name",
                    value=text_value(data.get("product_name"))
                )

            description = st.text_area(
                "Description",
                value=text_value(data.get("description")),
                height=120
            )


            # 2. Product specifications

            st.markdown("### Product Specifications")

            specs_df = st.data_editor(
                pd.DataFrame(
                    dict_to_rows(
                        data.get("product_specification", {})
                    ),
                    columns=["Field", "Value"]
                ),
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key=f"specs_{run_id}",
                column_config={
                    "Field": st.column_config.TextColumn(
                        "Specification"
                    ),
                    "Value": st.column_config.TextColumn(
                        "Value"
                    )
                }
            )


            # 3. Client and offers

            st.markdown("### Client & Offers")

            col3, col4 = st.columns(2)

            with col3:

                client_text = st.text_area(
                    "Clients / Dealers",
                    value=list_to_text(data.get("client", [])),
                    height=100,
                    help="Enter one client per line."
                )

            with col4:

                offer_text = st.text_area(
                    "Offers",
                    value=list_to_text(data.get("offer", [])),
                    height=100,
                    help="Enter one offer per line."
                )


            # 4. Contact information

            st.markdown("### Contact Information")

            contact_df = st.data_editor(
                pd.DataFrame(
                    contact_to_rows(data.get("contact", {})),
                    columns=["Contact Type", "Value"]
                ),
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key=f"contact_{run_id}"
            )


            # 5. Location information

            st.markdown("### Location")

            location_df = st.data_editor(
                pd.DataFrame(
                    dict_to_rows(data.get("location", {}))
                ),
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key=f"location_{run_id}",
                column_config={
                    "Field": st.column_config.TextColumn(
                        "Location Type"
                    ),
                    "Value": st.column_config.TextColumn(
                        "Location Detail"
                    )
                }
            )


            # 6. Missing and uncertain fields

            with st.expander(
                "Missing & Uncertain Information",
                expanded=bool(
                    data.get("missing_fields")
                    or data.get("uncertain_fields")
                )
            ):

                missing_text = st.text_area(
                    "Missing Fields",
                    value=list_to_text(
                        data.get("missing_fields", [])
                    ),
                    help="One field name per line."
                )

                uncertain_df = st.data_editor(
                    pd.DataFrame(
                        dict_to_rows(
                            data.get("uncertain_fields", {})
                        ),
                        columns=["Field", "Value"]
                    ),
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    key=f"uncertain_{run_id}",
                    column_config={
                        "Field": st.column_config.TextColumn(
                            "Field Name"
                        ),
                        "Value": st.column_config.TextColumn(
                            "Reason / Explanation"
                        )
                    }
                )


            st.divider()

            approve_clicked = st.form_submit_button(
                "Approve & Save Record",
                type="primary",
                use_container_width=True
            )


        # =================================================
        # 8. APPROVAL AND PYDANTIC VALIDATION
        # =================================================

        if approve_clicked:

            try:

                final_data = {

                    "ad_category": ad_category.strip() or None,

                    "ad_type": ad_type.strip() or None,

                    "client": text_to_list(client_text),

                    "brand": brand.strip() or None,

                    "headline": headline.strip() or None,

                    "description": description.strip() or None,

                    "product_name": product_name.strip(),

                    "product_specification": rows_to_dict(
                        specs_df,
                        "Field",
                        "Value"
                    ),

                    "price": price.strip() or None,

                    "offer": text_to_list(offer_text),

                    "contact": rows_to_contact(contact_df),

                    "location": rows_to_dict(
                        location_df,
                        "Field",
                        "Value"
                    ),

                    "missing_fields": text_to_list(missing_text),

                    "uncertain_fields": rows_to_dict(
                        uncertain_df,
                        "Field",
                        "Value"
                    )
                }


                # Validate against Pydantic schema

                approved_record = AdvertisementSchema.model_validate(
                    final_data
                )

                approved_json = approved_record.model_dump(
                    mode="json"
                )


                # Save approved record

                output_path = APPROVED_DIR / (
                    f"advertisement_{uuid.uuid4().hex}.json"
                )

                output_path.write_text(
                    json.dumps(
                        approved_json,
                        ensure_ascii=False,
                        indent=4
                    ),
                    encoding="utf-8"
                )


                # Create and save a structured Excel workbook from approved data.
                excel_path = output_path.with_suffix(".xlsx")
                excel_bytes = create_excel_workbook(approved_json)
                excel_path.write_bytes(excel_bytes)

                st.session_state.approved_json = approved_json
                st.session_state.approved_path = str(output_path)
                st.session_state.approved_excel_path = str(excel_path)

                st.rerun()


            except Exception as error:

                st.error(f"Validation or saving failed: {error}")


# =====================================================
# 9. UPLOADED IMAGE PREVIEW BEFORE EXTRACTION
# =====================================================

elif uploaded_file is not None:

    st.divider()
    st.subheader("Image Preview")

    st.image(
        uploaded_file,
        use_container_width=True
    )
