import sys
import json
from fpdf import FPDF
import os

def create_slips(json_path, font_path, out_pdf_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    voters = data.get("voters", [])
    polling_station = data.get("pollingStation", "ਸਰਕਵਰਚ ਐਲਚਮਮਟਰਚ ਸਕਬਲ, ਨਲਚਈਆਆ, ਹਹਜਸਆਰਪਹਰ")
    
    pdf = FPDF(unit="mm", format="A4")
    
    # Add the extracted font (we'll use the main one which is likely MPHIPK_ArialUnicodeMS or AAAAAB_ArialUnicodeMS)
    # Actually, we need to register the font
    pdf.add_font("CustomFont", style="", fname=font_path)
    pdf.set_font("CustomFont", size=10)
    
    pdf.add_page()
    
    # Draw a sample slip
    pdf.set_xy(10, 10)
    pdf.cell(0, 10, txt="ਪੋਿਲੰਗ:- " + polling_station, new_x="LMARGIN", new_y="NEXT")
    
    # Voter details
    if voters:
        voter = voters[0]
        pdf.cell(0, 10, txt=f"ਨਵਮ : {voter['name']}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, txt=f"ਪਤਚ/ਜਪਤਵ: {voter['relativeName']}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, txt=f"ਉਮਰ : {voter['age']}  ਜਲਨਗ: {voter['gender']}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, txt=f"Voter ID : {voter['voterId']}", new_x="LMARGIN", new_y="NEXT")
        
    pdf.output(out_pdf_path)
    print(f"Generated {out_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python generate_pdf.py <json_path> <font_path> <out_pdf_path>")
        sys.exit(1)
    
    create_slips(sys.argv[1], sys.argv[2], sys.argv[3])
