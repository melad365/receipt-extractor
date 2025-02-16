import streamlit as st
import google.generativeai as genai
import pandas as pd
import openpyxl
import io
import json
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key
api_key = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=api_key)

def extract_text_from_receipt(image_bytes):
    """Extract text from receipt using Google's Gemini API."""
    model = genai.GenerativeModel("gemini-1.5-flash")  # Use latest model

    response = model.generate_content([
    {"text": """
        Extract all text from this receipt image and return a **valid JSON object**. Do not include any extra formatting like code blocks, newlines, or explanations. The JSON must have the following headers:
        
        Ensure that:
        - I do not get markdown formatting
        - All keys are in **lowercase** for consistency.
        - `items` is an array of objects with `name`, `quantity`, and `price`.
        - `total_amount` is a **float** without currency symbols.
        - No additional text, explanations, or formatting (such as triple backticks) is included.
    """},
    {"mime_type": "image/jpeg", "data": image_bytes}  # Change to "image/png" for PNG
])

    # print(response)
    if response and response.text:
        text = response.candidates[0].content.parts[0].text
        json_str = text.replace("```json", "").replace("```", "")
        parsed_json = json.loads(json_str)
        print(json.dumps(parsed_json, indent=2))


    return (json.dumps(parsed_json, indent=2)) if response and response.text else "No text extracted"

def process_text(data):
    # Ensure data is a dictionary
    if isinstance(data, str):  
        try:
            data = json.loads(data)  # Convert string to dictionary
        except json.JSONDecodeError:
            print("Error: Invalid JSON format")
            return []  # Return empty list if JSON parsing fails

    # Extract 'Items' field (default to an empty list if missing)
    items = data.get("items", [])  # Assuming 'items' is a list

    # Process each item
    processed_items = []
    for item in items:
        if isinstance(item, dict):  # Ensure item is a dictionary
            name = item.get("name", "Unknown")
            quantity = item.get("quantity", 1)
            price = item.get("price", 0.0)

            processed_items.append({
                "name": name,
                "quantity": quantity,
                "price": price
            })
        else:
            processed_items.append(str(item))  # Fallback for unexpected types

    return processed_items


def save_to_excel(data, filename="receipts.xlsx"):
    """Save receipt data to an Excel file."""
    try:
        df = pd.read_excel(filename)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["Store", "Date", "Item", "Quantity", "Price", "Total"])
    
    rows = []
    for item in data["Items"]:
        rows.append([data["Store"], data["Date"], item["name"], item["quantity"], item["price"], data["Total"]])

    new_df = pd.DataFrame(rows, columns=df.columns)
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_excel(filename, index=False)

# Streamlit UI
st.title("Receipt Scanner 📄📊")

uploaded_file = st.file_uploader("Upload a receipt image", type=["jpg", "png", "jpeg", "heic"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Receipt")
    image_bytes = uploaded_file.getvalue()

    st.write("Extracting text from receipt...")
    extracted_text = extract_text_from_receipt(image_bytes)

    if extracted_text:
        structured_data = process_text(extracted_text)

        st.subheader("Extracted Data")
        st.json(structured_data)

        if st.button("Save to Excel"):
            save_to_excel(structured_data)
            st.success("Data saved to receipts.xlsx! ✅")
    else:
        st.error("Failed to extract text from the receipt.")
