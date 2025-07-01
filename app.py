from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from paddleocr import PPStructureV3
from typing import List, Dict
from datetime import datetime
from io import StringIO
import pandas as pd
import os
import json
import uvicorn
import cv2

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# PaddleOCR pipeline
pipeline = PPStructureV3()

# Config
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_image_if_needed(image_path, max_side_len=4000):
    img = cv2.imread(image_path)
    h, w = img.shape[:2]

    if max(h, w) > max_side_len:
        scale = max_side_len / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(image_path, img)
        print(f"Image resized to: {new_w}x{new_h}")

    return image_path

def sanitize(value):
    return "" if pd.isna(value) or str(value).lower() == 'nan' else str(value).strip()

def parse_ca_html(html_content: str) -> List[Dict[str, str]]:
    tables = pd.read_html(StringIO(html_content))
    if not tables:
        return []
    df = tables[0]

    cleaned_data = []
    for _, row in df.iterrows():
        if 'SEMESTER' in str(row[0]).upper() or str(row[0]).strip() in ['Paper Code(Unique Code)', '']:
            continue
        try:
            ca3_raw = sanitize(row[4])
            if 'Page Count' in ca3_raw:
                ca3_raw = ca3_raw.split('Page Count')[0].strip()

            record = {
                "paper_code": sanitize(row[0]),
                "paper_name": sanitize(row[1]),
                "ca1": sanitize(row[2]),
                "ca2": sanitize(row[3]),
                "ca3": ca3_raw,
                "ca4": sanitize(row[5]),
                "teacher": sanitize(row[6]) if len(row) > 6 else ""
            }
            cleaned_data.append(record)
        except Exception:
            continue
    return cleaned_data

def parse_pca_html(html_content: str) -> List[Dict[str, str]]:
    tables = pd.read_html(StringIO(html_content))
    if not tables:
        return []
    df = tables[0]

    cleaned_data = []
    for _, row in df.iterrows():
        if 'SEMESTER' in str(row[0]).upper() or str(row[0]).strip() in ['Paper Code(Unique Code)', '']:
            continue
        try:
            record = {
                "paper_code": sanitize(row[0]),
                "paper_name": sanitize(row[1]),
                "pca1": sanitize(row[2]),
                "pca2": sanitize(row[3]),
                "teacher": sanitize(row[6]) if len(row) > 6 else ""
            }
            cleaned_data.append(record)
        except Exception:
            continue
    return cleaned_data

def save_json_output(data: List[Dict[str, str]], filename: str) -> str:
    output_dir = 'processed_data'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.json"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    return output_path

@app.post("/process_ca_marks")
async def process_ca_marks(file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Only PNG, JPG, and JPEG files are allowed")

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)

    try:
        with open(filepath, "wb") as buffer:
            buffer.write(await file.read())

        resize_image_if_needed(filepath)

        output = pipeline.predict(filepath)

        if not output or not output[0]['table_res_list']:
            raise HTTPException(status_code=400, detail="No table data found in the image")

        html_content = output[0]['table_res_list'][0]['pred_html']
        parsed_data = parse_ca_html(html_content)

        if not parsed_data:
            raise HTTPException(status_code=400, detail="No valid CA data found in the table")

        json_path = save_json_output(parsed_data, file.filename)
        os.remove(filepath)

        return JSONResponse({
            "status": "success",
            "message": "CA marks processed successfully",
            "data": parsed_data,
            "json_path": json_path,
            "timestamp": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail=f"Error processing CA marks: {str(e)}")

@app.post("/process_pca_marks")
async def process_pca_marks(file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Only PNG, JPG, and JPEG files are allowed")

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)

    try:
        with open(filepath, "wb") as buffer:
            buffer.write(await file.read())

        resize_image_if_needed(filepath)

        output = pipeline.predict(filepath)

        if not output or not output[0]['table_res_list']:
            raise HTTPException(status_code=400, detail="No table data found in the image")

        html_content = output[0]['table_res_list'][0]['pred_html']
        parsed_data = parse_pca_html(html_content)

        if not parsed_data:
            raise HTTPException(status_code=400, detail="No valid PCA data found in the table")

        json_path = save_json_output(parsed_data, file.filename)
        os.remove(filepath)

        return JSONResponse({
            "status": "success",
            "message": "PCA marks processed successfully",
            "data": parsed_data,
            "json_path": json_path,
            "timestamp": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail=f"Error processing PCA marks: {str(e)}")

@app.get("/ca", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
@app.get("/pca", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("pca.html", {"request": request})
if __name__ == '__main__':
    uvicorn.run(app, port=8000)
