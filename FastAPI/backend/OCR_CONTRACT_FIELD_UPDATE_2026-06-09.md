# OCR 계약 필드 추출 업데이트 정리 - 2026-06-09

## 1. 오늘 업데이트한 핵심 내용

### 기본 OCR 후보 판단

- 무료 OCR 후보로 `EasyOCR`, `PaddleOCR`, `Tesseract`를 비교했다.
- 현재 Windows + Python 3.12 환경에서는 `EasyOCR`만 실제 벤치 실행에 성공했다.
- `PaddleOCR 3.6.0 + paddlepaddle 3.3.1`은 설치와 모델 다운로드까지 성공했지만 OCR 실행 중 Paddle 내부 oneDNN/PIR 오류가 발생했다.
- `PaddleOCR 2.7.3`도 NumPy 1.x 조정 후 모델 다운로드까지 됐지만 Paddle oneDNN 오류로 실패했다.
- `Tesseract`는 시스템에 `tesseract.exe`가 없어 실행 불가였다.
- 결론: 현 MVP 로컬 기본 OCR은 `EasyOCR`로 두는 것이 가장 현실적이다.

### EasyOCR 기본값 반영

수정 파일:

- `FastAPI/backend/app/config.py`
- `FastAPI/backend/requirements.txt`

변경:

```python
local_ocr_provider = os.getenv("LOCAL_OCR_PROVIDER", "easyocr").lower()
```

`requirements.txt`에 `easyocr`를 추가했다.

주의:

- 현재 프로젝트 경로가 깊어서 `backend/.venv`에 `easyocr/torch`를 설치할 때 Windows long path 오류가 발생했다.
- 짧은 경로의 벤치용 venv에서는 EasyOCR 설치와 실행이 성공했다.
- 다른 환경에서 실행할 때는 repo를 짧은 경로에 두거나 Windows long path를 활성화하는 것이 좋다.

---

## 2. OCR 보조 JSON 기능

### 목적

OCR 원문은 흔들리므로 `full_text`만 믿지 않고, 계약 핵심 필드를 구조화한 보조 JSON을 함께 생성한다.

응답 구조 목표:

```json
{
  "full_text": "...OCR 전체 텍스트...",
  "contract_fields": {
    "profile": {},
    "fields": {},
    "field_groups": {},
    "missing_fields": [],
    "low_confidence_fields": [],
    "needs_review": true
  },
  "text_locations": []
}
```

추가 파일:

- `FastAPI/backend/app/services/contract_field_service.py`

주요 역할:

- OCR 텍스트에서 계약 핵심 필드 추출
- OCR box 위치 정보(`ExtractedTextLocation`)를 사용해 각 필드의 근거 bbox 생성
- 필드별 `value`, `confidence`, `needs_review`, `evidence` 제공
- `evidence`에는 `page_number`, `bbox`, `coordinate_system`, `span_ids`, `text`, `match_confidence`, `ocr_confidence` 포함

업로드 응답 연결:

- `FastAPI/backend/app/schemas/document_schema.py`에 `contract_fields` 추가
- `FastAPI/backend/app/routers/upload_router.py`에서 `contract_field_service.extract_contract_fields(...)` 호출

---

## 3. 계약서 종류별 프로필

프론트 업로드 패널에 계약서 종류 선택 드롭다운을 추가했다.

선택값:

- `jeonse`: 전세
- `monthly_rent`: 월세
- `mixed_rent`: 반전세
- `sale`: 매매
- `unknown`: 모름

업로드 시 `FormData`에 추가:

```js
body.append("document_type", elements.documentType?.value || "unknown");
```

백엔드 Form 파라미터:

```python
document_type: ContractDocumentType | None = Form(default=ContractDocumentType.unknown)
```

### 전세 `jeonse`

필수:

- `contract_type`
- `deposit_amount`
- `lease_start_date`
- `lease_end_date`
- `landlord_name`
- `tenant_name`
- `address`

가능성 높음:

- `confirmed_date_status`
- `move_in_report_status`
- `priority_rights`
- `special_terms`
- `risk_flags`

### 월세 `monthly_rent`

필수:

- `contract_type`
- `deposit_amount`
- `monthly_rent`
- `lease_start_date`
- `lease_end_date`
- `landlord_name`
- `tenant_name`
- `address`

가능성 높음:

- `maintenance_fee`
- `payment_due_day`
- `confirmed_date_status`
- `move_in_report_status`
- `special_terms`
- `risk_flags`

### 반전세 `mixed_rent`

필수:

- `contract_type`
- `deposit_amount`
- `monthly_rent`
- `lease_start_date`
- `lease_end_date`
- `landlord_name`
- `tenant_name`
- `address`

가능성 높음:

- `maintenance_fee`
- `payment_due_day`
- `confirmed_date_status`
- `move_in_report_status`
- `priority_rights`
- `special_terms`
- `risk_flags`

### 매매 `sale`

필수:

- `contract_type`
- `sale_price`
- `seller_name`
- `buyer_name`
- `address`
- `contract_payment`
- `balance_payment`
- `ownership_transfer_date`

가능성 높음:

- `intermediate_payment`
- `mortgage_status`
- `registration_status`
- `special_terms`
- `risk_flags`

---

## 4. 정확도 개선 방식

### 단순 정규식만 쓰지 않음

초기에는 전체 OCR 텍스트에서 정규식만 돌렸는데 다음 오탐이 있었다.

- `임대인에거`를 임대인 이름으로 착각
- `제7조 채무불이행과 손해배상` 문장 안의 `임대인 또는 임차인`을 당사자 이름 문맥으로 착각
- `사무소소재지`를 계약 주소로 착각

### 라벨 주변 OCR box 기반 추출

계약서는 라벨-값 구조가 강하므로 다음 규칙을 반영했다.

- `보증금` 라벨 근처의 숫자 또는 한글 금액 추출
- `월세`, `차임`, `월 차임` 라벨 근처의 금액 추출
- `임대차기간`, `존속기간`, `기간` 라벨 근처 날짜 2개 추출
- `임대인` 다음 이름 후보 추출
- `임차인` 다음 이름 후보 추출
- `매매대금`, `계약금`, `중도금`, `잔금` 라벨 근처 금액 추출
- `소유권이전`, `이전등기` 라벨 근처 날짜 추출

### 한글 금액 파서

숫자 금액뿐 아니라 한글 금액도 보조 처리한다.

예:

- `삼억오천만원`
- `구천만원`
- `사십이만원`

### 오탐 방지 규칙

당사자명 추출은 다음 문맥에서는 채택하지 않도록 했다.

- `제 n 조`
- `또는`
- `불이행`
- `손해배상`
- `계약상`
- `상대방`
- `해지`
- `종료`

계약 조항의 `임대인 또는 임차인`은 당사자 정보가 아니라 일반 조항 문구이기 때문이다.

---

## 5. 제공 PDF 분석 결과

사용 파일:

- `Scan_20260607_182853_page_2.pdf`

OCR 결과:

- OCR 엔진: `EasyOCR`
- OCR 시간: 약 11초
- OCR box 수: 160개
- 한글 비율: 약 0.828

분석 판단:

- 이 파일은 이름상 `page_2`이고 실제 내용도 조항/서명 영역 위주다.
- 보증금, 임대차기간, 임대인, 임차인, 주소 등 핵심 정보가 있는 첫 페이지가 아닌 것으로 보인다.
- 따라서 `document_type=jeonse`를 줘도 `contract_type=전세` 외에는 대부분 `needs_review`로 남는 것이 맞다.
- 무리하게 값을 채택하지 않는 것이 안전하다.

최종 상태:

- `contract_type`: 사용자 입력 기반 `전세`, confidence 0.95
- `deposit_amount`: null
- `lease_start_date`: null
- `lease_end_date`: null
- `landlord_name`: null
- `tenant_name`: null
- `address`: null
- `missing_fields`: 보증금, 기간, 임대인, 임차인, 주소

---

## 6. 다른 환경에서 이어서 할 일

1. repo를 가능한 짧은 경로에 둔다.

예:

```text
C:/work/rental_scam_webpage
```

2. Python 3.12 또는 3.11 venv 생성

```powershell
cd FastAPI/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. EasyOCR 설치 시 Windows long path 오류가 나면:

- repo 경로를 더 짧게 옮긴다.
- Windows long path를 활성화한다.
- 또는 짧은 별도 venv를 사용한다.

4. 백엔드 실행

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

5. 프론트 실행

```powershell
cd FastAPI/frontend
python -m http.server 5173 --bind 127.0.0.1
```

6. 브라우저

```text
http://127.0.0.1:5173
```

업로드 API 사용 시 `document_type`을 FormData에 포함한다.

```text
document_type=jeonse
document_type=monthly_rent
document_type=mixed_rent
document_type=sale
document_type=unknown
```

---

## 7. 시행착오와 원인

### PaddleOCR 실패

PaddleOCR 3.x:

- 설치 성공
- 모델 다운로드 성공
- 실행 중 `ConvertPirAttribute2RuntimeAttribute` oneDNN/PIR 오류

PaddleOCR 2.x:

- 설치 성공
- NumPy ABI 문제 발생
- NumPy 1.26으로 낮춘 뒤 import는 개선
- 실행 중 `OneDnnContext does not have the input Filter` 오류

판단:

- 현재 Windows + Python 3.12 + PaddlePaddle 3.3.1 조합에서는 안정적이지 않다.
- PaddleOCR은 Python 3.10/3.11 또는 Linux 환경에서 별도 검증하는 것이 낫다.

### EasyOCR 설치 경로 문제

깊은 경로의 venv에서 `torch` 설치 중 긴 파일 경로 오류 발생.

해결:

- 짧은 경로 venv 사용
- repo를 짧은 경로로 이동
- Windows long path 활성화

---

## 8. 앞으로 보완할 점

### 전체 계약서 페이지 단위 처리

현재 `page_2` 하나만 분석하면 핵심 필드가 없는 경우가 많다.

개선:

- 전체 PDF 업로드 기준으로 모든 페이지 OCR
- 페이지별 역할 추정
  - 1페이지: 당사자, 주소, 금액, 기간
  - 2페이지 이후: 조항, 특약, 서명
- 핵심 필드는 앞 페이지 가중치 높게 적용

### OCR box 좌표 정밀도 개선

현재 evidence bbox는 OCR span window를 union한 값이다.

개선:

- 같은 행의 오른쪽 값만 bbox로 묶기
- 라벨 bbox와 값 bbox를 분리
- `label_bbox`, `value_bbox`를 따로 저장
- 프론트 하이라이트는 `value_bbox` 중심으로 표시

### 필드별 후처리

금액:

- 숫자 금액과 한글 금액 동시 검증
- 너무 작은 금액/너무 큰 금액 범위 필터
- 전세 보증금과 월세 차임의 단위 구분

날짜:

- `부터`, `까지`, `존속기간`, `인도일` 주변 날짜 구분
- 계약일과 임대차기간 시작일 혼동 방지

당사자명:

- 서명란 이름과 본문 당사자 이름 비교
- 주민등록번호/주소 마스킹 이후 이름 추출 손실 확인

주소:

- `사무소 소재지`와 `임차주택 소재지` 구분
- 중개사무소 주소를 계약 목적물 주소로 오인하지 않도록 라벨 구분

### 프론트 개선

- `field_groups.required`를 표로 표시
- `missing_fields`를 사용자 체크리스트로 표시
- `evidence` bbox 클릭 시 문서 보기에서 해당 위치 강조
- `needs_review` 필드는 노란색으로 표시
- 사용자 확인/수정값을 별도 `reviewed_fields`로 저장

---

## 9. 반드시 구분해야 할 것

### OCR 텍스트와 구조화 필드

- `full_text`: OCR 원문
- `contract_fields`: OCR 원문과 box를 바탕으로 추정한 구조화 결과

`contract_fields`는 법적 확정값이 아니라 후보값이다.

### 사용자 입력 계약 종류와 OCR 감지 계약 종류

- 사용자가 선택한 `document_type`: 신뢰도 높은 입력값
- OCR에서 감지한 `contract_type`: 보조 판단

사용자 입력이 있으면 프로필 선택에는 사용자 입력을 우선한다.

### 라벨 bbox와 값 bbox

현재는 evidence bbox가 라벨+값을 같이 포함할 수 있다.

향후에는 `label_bbox`, `value_bbox`를 분리하는 것이 좋다.

### 필수 필드와 가능성 높은 필드

필수 필드:

- 해당 계약서 종류에서 반드시 확인해야 하는 항목

가능성 높은 필드:

- 있으면 위험 분석에 도움이 되지만, 모든 계약서에 반드시 있지는 않은 항목

### null과 오탐

값을 잘못 채택하는 것보다 `null + needs_review`가 낫다.

계약/부동산 문서는 오탐이 사용자에게 잘못된 판단을 줄 수 있으므로, confidence가 낮으면 과감하게 확인 필요로 보내야 한다.

---

## 10. 다음 작업 우선순위

### P0. 전체 계약서 PDF로 재검증

현재 제공받은 파일은 `page_2` 단일 페이지라 핵심 필드가 대부분 없는 페이지였다.

가장 먼저 해야 할 일:

- 계약서 전체 PDF 또는 최소 1페이지를 확보한다.
- `document_type=jeonse`로 분석한다.
- 보증금, 임대인, 임차인, 주소, 기간이 실제로 잡히는지 확인한다.

성공 기준:

- 전세 계약서 1페이지에서 `required_fields`의 5개 이상이 채워진다.
- 채워진 필드에는 `evidence[0].bbox`가 있다.
- 잘못된 값보다 `null + needs_review`가 우선되어야 한다.

### P1. `label_bbox`와 `value_bbox` 분리

현재 evidence bbox는 라벨과 값이 함께 묶일 수 있다.

추천 구조:

```json
{
  "label": "보증금",
  "value": 350000000,
  "evidence": [
    {
      "label_bbox": [100, 200, 180, 230],
      "value_bbox": [190, 200, 360, 230],
      "page_number": 1
    }
  ]
}
```

### P2. 사용자 확인 UI

OCR 결과는 후보값이므로 사용자가 확인/수정할 수 있어야 한다.

추천 UI:

- 필수 필드 표
- 값이 있으면 초록/회색
- `needs_review`면 노란색
- 누르면 문서 bbox 위치 강조
- 사용자가 직접 값 수정 가능

저장 구조:

```json
{
  "reviewed_fields": {
    "deposit_amount": {
      "value": 350000000,
      "source": "user_confirmed"
    }
  }
}
```

### P3. 위험 분석과 필드 JSON 연결

- `priority_rights`가 있으면 위험 점수 가중
- `move_in_report_status`에 제한/유예가 있으면 고위험
- `confirmed_date_status`에 동의/제한/불가가 있으면 고위험
- `special_terms`에서 보증금 반환 지연 문구가 있으면 고위험

---

## 11. 테스트 매트릭스

| 계약 종류 | 샘플 상태 | 기대 결과 |
|---|---|---|
| 전세 | 깨끗한 PDF 1페이지 | 보증금, 기간, 임대인, 임차인, 주소 추출 |
| 전세 | 스캔 PDF 1페이지 | 일부 필드 추출, 낮은 confidence는 needs_review |
| 전세 | 2페이지 조항만 | 대부분 missing_fields 처리 |
| 월세 | 보증금+월차임 있음 | deposit_amount, monthly_rent 둘 다 추출 |
| 반전세 | 큰 보증금+월세 있음 | mixed_rent profile 적용 |
| 매매 | 매도인/매수인/매매대금 있음 | sale profile 필수 필드 추출 |
| 매매 | 임대차 문구 없음 | 임대인/임차인 필드에 억지 매칭 금지 |

테스트할 오탐 문장:

```text
임대인 또는 임차인이 계약상 의무를 불이행한 경우
```

기대:

- `landlord_name`과 `tenant_name`으로 채택되면 안 된다.

테스트할 금액 문장:

```text
보증금 금 삼억오천만원정
월 차임 금 사십이만원정
```

기대:

- `deposit_amount = 350000000`
- `monthly_rent = 420000`

---

## 12. 개발자가 바로 확인할 명령

백엔드 문법 검사:

```powershell
cd FastAPI/backend
.venv\Scripts\python.exe -m compileall app
```

FastAPI import 확인:

```powershell
.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```

프론트 JS 문법 확인:

```powershell
node --check FastAPI/frontend/app.js
```

단일 PDF 분석:

```powershell
python work/analyze_contract_pdf.py C:\path\to\contract.pdf --backend-dir FastAPI/backend --output outputs/contract_ocr.json --document-type jeonse
```

---

## 13. 설계상 중요한 결정

### 사용자 입력 `document_type`을 우선한다

OCR이 `전세`, `월세`, `차임` 같은 단어를 조항에서 많이 읽기 때문에 실제 계약 종류 판별을 OCR에만 맡기면 오판이 생긴다. 사용자가 업로드 전에 선택한 종류는 프로필 선택에 가장 좋은 신호다.

따라서:

- 프로필 선택은 사용자 입력 우선
- OCR 감지는 보조 신호

### 값이 없으면 비워둔다

계약서 분석에서 가장 위험한 것은 `missing`이 아니라 `wrong value`다.

원칙:

- 근거가 약하면 `null`
- `needs_review: true`
- `missing_fields`에 넣기

### OCR bbox는 추출값의 근거이지 정답이 아니다

OCR bbox는 스캔 기울기, 박스 병합, 한글 오인식 등으로 흔들릴 수 있다. bbox는 사용자 확인을 돕는 evidence로 쓰고, 법적 판단의 근거로 단독 사용하면 안 된다.

---

## 14. 추천 데이터 구조 최종안

```json
{
  "profile": {
    "document_type": "jeonse",
    "label": "전세",
    "required_fields": [],
    "likely_fields": []
  },
  "field_groups": {
    "required": {},
    "likely": {},
    "other": {}
  },
  "fields": {
    "deposit_amount": {
      "value": 350000000,
      "display_value": "₩350,000,000",
      "confidence": 0.91,
      "needs_review": false,
      "evidence": [
        {
          "page_number": 1,
          "label_text": "보증금",
          "value_text": "350,000,000원",
          "label_bbox": [],
          "value_bbox": [],
          "coordinate_system": "easyocr_pdf_rendered_pixels_2x",
          "span_ids": []
        }
      ]
    }
  },
  "missing_fields": [],
  "low_confidence_fields": [],
  "needs_review": false
}
```

---

## 15. 인수인계 한 줄 요약

현재 코드는 OCR 결과에서 계약 핵심 정보를 뽑는 1차 구조를 갖췄고, 계약 종류별 프로필과 OCR bbox evidence까지 붙인다. 다만 전체 계약서 첫 페이지 기준의 실전 검증이 아직 필요하며, 다음 핵심 개선은 `label_bbox/value_bbox` 분리와 사용자 확인 UI다.
