import fitz
import sys
import json

def extract(pdf_path):
    doc = fitz.open(pdf_path)
    page1_text = doc[0].get_text("text")
    
    # Just extract raw text from page 2 to check unicode
    page2_text = doc[1].get_text("text")
    
    out = {
        "page1": page1_text,
        "page2": page2_text[:2000] # First 2000 chars
    }
    
    with open("python_json_output.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    extract("C:/Users/Aman/Downloads/1-2.pdf")
