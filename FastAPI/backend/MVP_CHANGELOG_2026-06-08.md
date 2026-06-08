# MVP 변경 정리 - 2026-06-08

이 문서는 `rental_scam_webpage/FastAPI/backend`에 반영할 백엔드 변경점을 다른 세션이나 다른 사람이 바로 이어서 읽을 수 있도록 정리한 기록입니다.

## 목표 플로우

1. 사용자가 PDF, 스캔본, 휴대폰 사진 계약서를 업로드한다.
2. 서버가 문자 추출과 기본 보안 검사를 수행한다.
3. 문자 추출 단계에서 리포트에 필요한 중요 키워드와 위치 정보를 함께 수집한다.
4. 재추출이 필요한 경우 원본 파일을 다시 요구하지 않고 캐시된 추출 결과를 우선 사용한다.
5. 법률 AI 분석 결과를 JSON으로 받아 위험 문구와 특약 설명을 리포트에 연결한다.
6. 리포트에는 위험 문구 색상, 하이라이트 위치, 특약 설명, 체크리스트를 함께 제공한다.
7. 사용자가 저장하거나 종료하면 삭제 정책에 따라 업로드 원본과 캐시를 정리한다.

## 주요 변경

### OCR 및 위치 정보

- `app/utils/pdf_utils.py`
  - PDF 텍스트 레이어가 비어 있는 스캔 PDF 페이지는 PyMuPDF로 이미지 렌더링한 뒤 OCR fallback을 수행합니다.
  - `PDF_OCR_RENDER_SCALE` 설정으로 렌더링 배율을 조절할 수 있습니다.
- `app/services/image_service.py`
  - 이미지 OCR 결과에서 `page_number`, `bbox`, `confidence`, `source`를 포함한 위치 데이터를 생성합니다.
  - 기울어짐, 스캔본, 모바일 촬영본 대응을 위해 threshold, 회전 후보, PSM 후보를 비교합니다.
  - 후보 비교는 빠른 텍스트 OCR로 수행하고, 최종 선택 후보에 대해서만 bbox OCR을 수행해 속도를 줄였습니다.
  - 후보 선택 점수는 한글, 숫자, 계약서 핵심 단어를 우선하도록 조정했습니다.
- `app/schemas/extraction_schema.py`
  - `ExtractedTextLocation`, `RedactionTarget`, `RedactionMetrics`를 추가했습니다.
  - 프론트엔드는 `bbox`와 `page_number`를 사용해 PDF/이미지 위에 하이라이트나 마스킹 박스를 그릴 수 있습니다.

### 추출 캐시 정책

- `app/services/extraction_cache_service.py`
  - 현재는 프로세스 메모리 dict 기반 TTL 캐시입니다.
  - `document_id`와 `content_hash` 기준 조회를 지원합니다.
  - 삭제 API에서 document cache purge가 가능하도록 인터페이스를 분리했습니다.
  - 운영 배포에서는 Redis 또는 DB-backed cache 구현체로 교체하는 것을 권장합니다.

### 개인정보 마스킹

- `app/services/redaction_service.py`
  - 표준 임대차 계약서 양식의 위치 기반 template redaction을 추가했습니다.
  - OCR 라벨 기반 redaction과 정규식 기반 redaction을 함께 사용합니다.
  - 주민등록번호, 전화번호, 계좌번호 같은 고위험 값은 `opaque` 마스킹 대상으로 분류합니다.
  - 이름, 주소, 공인중개사 정보 등은 `mosaic` 또는 반투명 표시 대상으로 분류할 수 있게 `mask_style`, `opacity`, `sensitivity` 필드를 제공합니다.
  - 마스킹된 OCR span은 `is_redacted`, `redaction_type`, `redaction_id`로 추적됩니다.
- `app/routers/upload_router.py`
  - 업로드 응답에 `text_locations`, `redactions`, `redaction_metrics`를 포함합니다.
  - `DELETE_RAW_UPLOAD_AFTER_OCR=true`이면 OCR 직후 원본 업로드 파일을 삭제합니다.

### 리포트 및 체크리스트

- `app/schemas/report_schema.py`
  - `ReportDifference.locations`와 `special_term_explanation`을 추가했습니다.
  - `SafetyChecklistItem`, `SafetyChecklistGroup`, `ReportResponse.safety_checklist`를 추가했습니다.
  - `RiskScoreBreakdown`과 `ReportResponse.risk_score`를 추가했습니다.
  - `ChecklistExternalAction`을 추가해 체크리스트 항목별 외부 확인 페이지 이동 버튼을 만들 수 있게 했습니다.
- `app/services/safety_checklist_service.py`
  - 계약 전, 계약 당일, 계약 후 단계별 체크리스트 틀을 제공합니다.
  - 등기부등본, 건축물대장, 보증보험, 중개사 조회 등 정부/공식 링크를 나중에 UI 박스에 붙이기 쉽게 `official_url`, `action_label`, `priority`, `stage`를 포함합니다.
  - `external_action.label`, `external_action.url`, `external_action.completion_hint`를 내려주므로 프론트는 사용자가 원할 때 공식 확인 페이지로 이동시키고, 확인 후 체크 완료 처리를 할 수 있습니다.
- `app/services/risk_score_service.py`
  - MVP 위험 점수 산식을 분리했습니다.
  - 기본 위험 점수 20점에 특약 위험도를 더하고, 완료된 체크리스트의 `risk_reduction_points`를 차감합니다.
  - 예시 mock report 기준 기본 점수는 `20 + high(8) + medium(4) = 32점`입니다.
  - `GET /reports/{document_id}?completed_checks=registry_owner_check&completed_checks=fixed_date_check`처럼 완료 체크 항목을 넘기면 점수가 낮아집니다.
- `app/services/analysis_service.py`
  - MVP용 mock 분석 응답에 위험 문구 설명, 권장 조치, 체크리스트를 연결했습니다.

### 삭제 절차

- `app/routers/retention_router.py`
  - `DELETE /retention/documents/{document_id}`에서 업로드 파일 삭제, 캐시 삭제, 메타데이터 삭제 표시를 수행합니다.
- `app/services/file_service.py`
  - 업로드 파일 삭제 유틸을 제공합니다.

## 환경 변수

로컬 OCR 테스트에 사용한 값:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:TESSDATA_PREFIX = "C:\Users\USER\Desktop\FastAPI\tools\tessdata"
$env:TESSERACT_LANG = "kor"
$env:OCR_TIMEOUT_SECONDS = "120"
$env:PDF_OCR_RENDER_SCALE = "2.0"
$env:DELETE_RAW_UPLOAD_AFTER_OCR = "true"
$env:PRIVACY_TEMPLATE_REDACTION_ENABLED = "true"
```

주의: Tesseract 실행 파일과 `kor.traineddata`는 Python package가 아니므로 배포 환경에 별도로 설치해야 합니다.

## 검증 기록

- `python -m compileall app` 통과.
- 4페이지 스캔 PDF 기준 OCR fallback 동작 확인.
- 개인정보 마스킹 정책 테스트 결과:
  - redaction count: 66
  - template redaction count: 51
  - redacted location count: 388
  - average box confidence: 약 0.86
  - OCR 후 `uploads` 원본 삭제 확인.
- 리포트 API에서 체크리스트 3개 그룹, 10개 항목 반환 확인.

## GitHub에 올리지 않을 항목

다음은 로컬 테스트 또는 민감정보 가능성이 있는 산출물이므로 커밋 대상에서 제외합니다.

- `venv/`
- `uploads/`
- `redaction_preview/`
- `redaction_preview_template/`
- `ocr_preview/`
- `__pycache__/`
- `.pytest_cache/`
- 로컬 DB 파일
- 샘플 계약서 원본 또는 OCR 결과 JSON
