import pdfplumber
import json
import re
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from datetime import datetime
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import uvicorn
from typing import List, Dict
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_json_output(data: List[Dict[str, str]], filename: str) -> str:
    output_dir = 'processed_data'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.json"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    return output_path
def extract_marksheet_data(pdf_path):
    student_info = {}
    subjects = []
    total_credits = 0
    total_credit_points = 0
    sgpa = None
    result = None
    clean_marks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        tables = first_page.extract_tables()
        
        # Extract student information
        student_line = re.search(r'NAME\s*:\s*(.*?)\s*ROLL NO\.?\s*:\s*(.*?)\n', text, re.IGNORECASE)
        if student_line:
            student_info["name"] = student_line.group(1).strip()
            student_info["roll_no"] = student_line.group(2).strip()
        
        student_info["roll_no"] = re.search(r'ROLL NO\.?\s*:\s*(.*?)\n', text, re.IGNORECASE).group(1).strip()
        student_info["registration_no"] = re.search(r'REGISTRATION NO\s*:\s*(.*?)\n', text, re.IGNORECASE).group(1).strip()
        
        # Extract SGPA and Result
        sgpa = re.search(r'SGPA.*?:\s*(\d+\.\d+)', text, re.IGNORECASE).group(1).strip()
        result = re.search(r'RESULT.*?:\s*(\w+)', text, re.IGNORECASE).group(1).strip()
        
        # Process the main table with subjects
        for table in tables:
            # Find the header row index
            header_row_idx = None
            for i, row in enumerate(table):
                if row and any("Subject Code" in str(cell) for cell in row):
                    header_row_idx = i
                    break
            
            if header_row_idx is not None:
                # Process subject rows
                for row in table[header_row_idx+1:]:
                    # Skip empty rows and summary rows
                    if not row or len(row) < 6 or "Total" in str(row[0]):
                        continue
                    
                    # Clean each cell
                    row = [str(cell).strip() if cell is not None else "" for cell in row]
                    
                    # Skip rows that don't look like subject data
                    if not row[0] or not any(c.isdigit() for c in row[0]):
                        continue
                    
                    try:
                        credit = float(row[4]) if row[4] else 0
                        credit_points = float(row[5]) if row[5] else 0
                        
                        subjects.append({
                            "subject_code": row[0],
                            "subject": row[1],
                            "grade": row[2],
                            "points": row[3],
                            "credit": row[4],
                            "credit_points": row[5]
                        })
                        
                        total_credits += credit
                        total_credit_points += credit_points
                    except (ValueError, IndexError) as e:
                        continue
        
        # Create the output structure
        output = {
            "student_info": student_info,
            "subjects": subjects,
            "total": {
                "total_credits": str(total_credits),
                "total_credit_points": str(total_credit_points)
            },
            "sgpa": sgpa,
            "result": result,
            "university": "Maulana Abul Kalam Azad University of Technology, West Bengal"
        }
        clean_marks.append(output)
    
    return clean_marks

@app.post("/process_semester_marks")
async def process_semester_marks(file:UploadFile=File(...)):
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    try:
        with open(filepath, "wb") as buffer:
            buffer.write(await file.read())
        output = extract_marksheet_data(filepath)
        if not output:
            raise HTTPException(status_code=400, detail="No table data found in the pdf")
        json_path = save_json_output(output, file.filename)
        os.remove(filepath)
        return JSONResponse({
            "status": "success",
            "message": "Semester marks processed successfully",
            "data": output,
            "json_path": json_path,
            "timestamp": datetime.now().isoformat()
        })
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail=f"Error processing semester marks: {str(e)}")

@app.get("/semester", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("semester.html", {"request":request})

if __name__ == '__main__':
    uvicorn.run(app, port=8000)
