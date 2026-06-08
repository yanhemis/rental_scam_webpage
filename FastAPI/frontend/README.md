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

## 핵심 추출 정보

파일 업로드 성공 시 `DocumentUploadResponse.full_text`를 사용해 다음 값을 화면에 표시합니다.

- 계약 유형
- 보증금
- 임대차 기간
- 확정일자 상태
- 전입신고 상태
- 선순위 권리 확인 상태

값이 비어 있는 표준 양식이거나 OCR에서 확정하기 어려운 경우 `확인 필요`로 표시합니다.
