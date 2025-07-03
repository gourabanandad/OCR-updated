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
    sgpa = None
    result = None
    clean_marks = []
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        tables = page.extract_tables()

        for table in tables:
            for row in table:
                if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                    continue

                joined_row = " ".join([cell for cell in row if cell])

                if "SGPA" in joined_row:
                    sgpa = re.sub(r".*SGPA.*:", "", row[0]).strip()

                elif "RESULT" in joined_row:
                    result = re.sub(r".*RESULT.*:", "", row[0]).strip()

    output = {
        "sgpa": sgpa,
        "result": result
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
