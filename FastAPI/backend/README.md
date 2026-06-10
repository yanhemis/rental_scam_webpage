# FastAPI backend

This branch is the PaddleOCR deployment/test branch.

## Runtime

- Recommended Python: 3.11
- OCR provider: PaddleOCR
- API base URL: `http://127.0.0.1:8001/api` for local frontend testing

PaddleOCR and `paddlepaddle` are sensitive to Python/runtime versions. Use the same interpreter for installing dependencies and starting the server.

## Local setup

```powershell
cd C:\Users\USER\Desktop\FastAPI\_github_publish\FastAPI\backend
py -3.11 -m venv ..\.venv-paddle
..\.venv-paddle\Scripts\python.exe -m pip install -r requirements.txt
```

## Start server

```powershell
$env:LOCAL_OCR_PROVIDER = "paddleocr"
$env:PDF_OCR_RENDER_SCALE = "2.0"
$env:OCR_TIMEOUT_SECONDS = "240"
$env:PRIVACY_TEMPLATE_REDACTION_ENABLED = "true"
$env:DELETE_RAW_UPLOAD_AFTER_OCR = "true"
$env:CLOVA_MOCK_ENABLED = "true"
..\.venv-paddle\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## Frontend test URL

Serve `FastAPI/frontend` and open:

```text
http://127.0.0.1:5173/index.html?api=http://127.0.0.1:8001/api
```

## Notes

- Do not run this branch with a different Python than the one used to install `requirements.txt`.
- If `paddleocr` fails to import, recreate the virtual environment with Python 3.11 and reinstall dependencies.
- Personal information redactions are opaque. General evidence boxes remain transparent highlights.
