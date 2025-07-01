# Marks Processing System

A FastAPI application that processes marksheet images using PaddleOCR to extract structured mark data.

## ✨ Features

* Upload marksheet images (PNG/JPG/JPEG)
* Extract tabular data using PaddleOCR
* Parse and validate subject codes, marks, and teacher names
* Display results in a user-friendly table
* Save processed data as JSON files

## 🚀 Installation

### ✅ Prerequisites

* Python 3.9+
* pip

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/marks-processing-system.git
cd marks-processing-system
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# On Linux/Mac
source venv/bin/activate
# On Windows
venv\Scripts\activate
```

### 3. Install PaddleOCR and dependencies

#### CPU version:

```bash
pip install paddlepaddle==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
```

#### GPU version (CUDA 11.8):

```bash
pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
```

#### Install PaddleOCR:

```bash
pip install paddleocr
```

### 4. Install other dependencies

```bash
pip install -r requirements.txt
```

If you don’t have `requirements.txt` yet, create it with:

```text
fastapi==0.95.2
uvicorn==0.22.0
paddleocr==2.6.1.3
pandas==2.0.2
python-multipart==0.0.6
jinja2==3.1.2
```

## ⚙️ Configuration

If using GPU, specify the device when initializing PaddleOCR:

```python
ocr = PaddleOCR(use_angle_cls=True, lang='en', det_db_box_thresh=0.4, use_gpu=True)
```

Or if you're using PPStructureV3:

```python
from paddleocr import PPStructureV3
pipeline = PPStructureV3(device='gpu')  # Change to 'cpu' if needed
```

## ▶️ Running the Application

```bash
uvicorn app:app --reload
```

Access the app in your browser:

* Frontend: [http://localhost:8000](http://localhost:8000)
* API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📷 Usage

1. Open the frontend at `http://localhost:8000`
2. Upload a marksheet image (PNG/JPG/JPEG)
3. View extracted marks in table format
4. JSON output is saved in the `processed_data/` folder

## 🗂️ Project Structure

```
marks-processing-system/
├── app.py               # FastAPI application logic
├── README.md             # Project documentation
├── requirements.txt      # Dependencies list
├── templates/
│   └── index.html        # Frontend template
├── static/ 
    └── style.css              # Static assets (CSS/JS)

```

## 📚 Documentation

* [PaddleOCR Official Docs](https://paddlepaddle.github.io/PaddleOCR/main/en/index.html)
* [FastAPI Docs](https://fastapi.tiangolo.com/)

## 🐳 Optional: Docker Setup

*Coming soon...*

## 🛆 Deployment

For production:

* Use Gunicorn with Uvicorn workers:

  ```bash
  gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```

* Set up environment variables for config, logging, etc.

* Use Nginx as reverse proxy

## 🤝 Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature-xyz`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature-xyz`)
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
