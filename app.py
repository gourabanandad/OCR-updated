from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from paddleocr import PPStructureV3
import pandas as pd
from io import StringIO
import os
from typing import List, Dict
import uvicorn
from datetime import datetime
import json
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
# Initialize PaddleOCR pipeline
pipeline = PPStructureV3()

# Configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_marks_html(html_content: str) -> List[Dict[str, str]]:
    """Parse the HTML table from paddleocr and return clean JSON data"""
    tables = pd.read_html(StringIO(html_content))
    if not tables:
        return []
    
    df = tables[0]
    
    cleaned_data = []
    for _, row in df.iterrows():
        # Skip header rows and semester title rows
        if row[0] == 'Paper Code(Unique Code)' or 'SEMESTER' in str(row[0]):
            continue
            
        # Extract CA3 value (remove "Page Count" portion)
        ca3_value = str(row[4])
        if 'Page Count' in ca3_value:
            ca3_value = ca3_value.split('Page Count')[0].strip()
        
        # Create cleaned record
        record = {
            "paper_code": str(row[0]).strip(),
            "paper_name": str(row[1]).strip(),
            "ca1": str(row[2]).strip() if pd.notna(row[2]) else "",
            "ca2": str(row[3]).strip() if pd.notna(row[3]) else "",
            "ca3": ca3_value,
            "ca4": str(row[5]).strip() if pd.notna(row[5]) else "",
            "teacher": str(row[6]).strip() if pd.notna(row[6]) else ""
        }
        
        # Remove empty values (convert to empty strings)
        for key in record:
            if record[key] == 'nan':
                record[key] = ""
        
        cleaned_data.append(record)
    
    return cleaned_data

def save_json_output(data: List[Dict[str, str]], filename: str) -> str:
    """Save the processed data to a JSON file"""
    output_dir = 'processed_data'
    os.makedirs(output_dir, exist_ok=True)
    
    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.json"
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
        
    return output_path

@app.post("/process_marks")
async def process_marks(file: UploadFile = File(...)):
    """
    Endpoint to process marksheet image and return structured data
    """
    # Validate file
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Only PNG, JPG, and JPEG files are allowed")
    
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    
    try:
        # Save the uploaded file
        with open(filepath, "wb") as buffer:
            buffer.write(await file.read())
        
        # Process the image with PaddleOCR
        output = pipeline.predict(filepath)
        
        # Validate we got table results
        if not output or not output[0]['table_res_list']:
            raise HTTPException(status_code=400, detail="No table data found in the image")
            
        html_content = output[0]['table_res_list'][0]['pred_html']
        
        # Parse the HTML to clean JSON
        parsed_data = parse_marks_html(html_content)
        
        if not parsed_data:
            raise HTTPException(status_code=400, detail="No valid marks data found in the table")
        
        # Save the processed data to JSON
        json_path = save_json_output(parsed_data, file.filename)
        
        # Clean up - remove the uploaded file after processing
        os.remove(filepath)
        
        return JSONResponse({
            "status": "success",
            "message": "Marks processed successfully",
            "data": parsed_data,
            "json_path": json_path,
            "timestamp": datetime.now().isoformat()
        })
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # Clean up if something went wrong
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail=f"Error processing marks: {str(e)}")
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
if __name__ == '__main__':
    uvicorn.run(app, port=8000)