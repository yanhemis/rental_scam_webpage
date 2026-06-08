# 발표용 프론트 MVP

계약서 업로드, 핵심 추출 정보, 계약서 보기, 위험 점수, 체크리스트를 한 화면에서 확인하는 정적 프론트입니다.

## 실행

backend 서버:

```powershell
cd C:\Users\USER\Desktop\FastAPI\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

frontend 서버:

```powershell
cd C:\Users\USER\Desktop\FastAPI\frontend
python -m http.server 5173 --bind 127.0.0.1
```

브라우저에서 엽니다.

```text
http://127.0.0.1:5173
```

## 연결 API

- `POST http://127.0.0.1:8000/api/documents/upload`
- `GET http://127.0.0.1:8000/api/reports/{document_id}`
- `GET http://127.0.0.1:8000/api/reports/{document_id}?completed_checks=registry_owner_check`

업로드 API가 실패하거나 backend가 꺼져 있으면 발표 흐름이 끊기지 않도록 demo report를 fallback으로 표시합니다.

