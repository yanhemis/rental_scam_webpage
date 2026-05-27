# UPDATE_README-TG

## 2026-05-27

### 작업 제목
- OCR 계약서 텍스트 기반 핵심 필드 구조화 추출 기능 추가

### 작업 목표
- 업로드/OCR 이후 생성된 계약서 텍스트에서 전세사기 예방 분석에 필요한 핵심 정보를 rule-based 방식으로 추출한다.
- 추출 결과를 API로 조회하고, 이후 위험 분석 또는 Clova 분석 단계에서 재사용할 수 있는 구조로 분리한다.

### 추가된 주요 기능
1. 계약 핵심 정보 추출 스키마 추가
   - 파일: `FastAPI/backend/app/schemas/contract_extract_schema.py`
   - 모델: `ExtractedContractInfo`
   - 포함 필드:
     - `document_id`
     - `contract_type`
     - `deposit_amount`
     - `lease_start_date`
     - `lease_end_date`
     - `confirmed_date_status`
     - `move_in_report_status`
     - `priority_rights`
     - `address`
     - `landlord_name`
     - `tenant_name`
     - `special_terms`
     - `missing_fields`
     - `field_confidence`

2. 계약 필드 추출 서비스 추가
   - 파일: `FastAPI/backend/app/services/contract_extract_service.py`
   - OCR/PDF 텍스트 추출 레이어와 분리된 별도 서비스로 구현했다.
   - 주요 함수:
     - `normalize_ocr_text`
     - `extract_contract_type`
     - `extract_deposit_amount`
     - `extract_lease_period`
     - `extract_confirmed_date_status`
     - `extract_move_in_report_status`
     - `extract_priority_rights`
     - `extract_address`
     - `extract_party_names`
     - `extract_special_terms`
     - `extract_contract_fields`

3. 1차 필수 필드 추출 구현
   - `contract_type`
     - 전세, 월세, 주택임대차, 매매 관련 키워드 기반 인식
   - `deposit_amount`
     - `350,000,000원`
     - `3억 5천만원`
     - `삼억오천만원`
     - 억/만/천/백/십 단위 기반 금액 정규화
   - `lease_start_date`
   - `lease_end_date`
     - `2026.08.01`
     - `2026-08-01`
     - `2026년 8월 1일`
     - `YYYY-MM-DD` 형식으로 정규화

4. 확장 필드 추출 구현
   - `confirmed_date_status`
     - 확정일자 관련 문맥에서 완료/예정/없음/미정 인식
   - `move_in_report_status`
     - 전입신고 관련 문맥에서 완료/예정/없음/미정 인식
   - `priority_rights`
     - 선순위, 근저당, 저당권, 가압류, 압류, 전세권, 담보권 등 권리관계 키워드 인식
   - `address`
     - 소재지, 주소, 임대차 목적물, 목적물의 표시, 부동산의 표시 문맥 기반 추출
   - `landlord_name`, `tenant_name`
     - 임대인/집주인, 임차인/세입자 라벨 기반 이름 추출
   - `special_terms`
     - 특약/특약사항 영역의 조항 목록 추출

5. 누락 필드 및 신뢰도 처리
   - 추출 실패 또는 빈 값은 `missing_fields`에 자동 포함된다.
   - 모든 대상 필드는 `field_confidence`에 0.0-1.0 범위의 confidence 값을 포함한다.
   - 시작일과 종료일은 각각 별도 confidence 키를 가진다.

### 저장 구조 변경
1. OCR 텍스트 캐시 저장 추가
   - 파일: `FastAPI/backend/app/services/storage_service.py`
   - 저장 위치:
     - `uploads/derived/{document_id}.ocr.txt`

2. 계약 필드 추출 결과 캐시 저장 추가
   - 저장 위치:
     - `uploads/derived/{document_id}.contract_fields.json`
   - DB 스키마 변경 없이 파일 기반 artifact로 우선 저장한다.
   - 이후 DB 영속 저장 또는 위험 분석 서비스 연결로 확장하기 쉬운 구조로 분리했다.

### API 변경사항
1. 필수 조회 API 추가
   - 파일: `FastAPI/backend/app/routers/upload_router.py`
   - 엔드포인트:
     - `GET /api/documents/{document_id}/extracted-fields`
   - 동작:
     - 저장된 추출 결과가 있으면 캐시 결과를 반환한다.
     - 캐시가 없으면 저장된 OCR 텍스트를 사용해 추출한다.
     - OCR 텍스트 캐시도 없으면 기존 파일 경로와 content type을 사용해 OCR을 재실행한 뒤 추출한다.

2. 수동 재추출 API 추가
   - 엔드포인트:
     - `POST /api/documents/{document_id}/extract-fields`
   - 동작:
     - 캐시된 OCR 텍스트를 기준으로 계약 필드를 다시 추출하고 저장한다.
     - OCR 텍스트가 없으면 OCR을 먼저 실행한다.

3. 관리자 재추출 API 추가
   - 파일: `FastAPI/backend/app/routers/admin_router.py`
   - 엔드포인트:
     - `POST /api/admin/documents/{document_id}/retry-extract-fields`
   - 동작:
     - 관리자 흐름에서 계약 필드 추출을 재실행한다.
     - 추출 결과를 `ExtractedContractInfo` 형태로 반환한다.

4. 관리자 OCR 재시도 흐름 보강
   - `POST /api/admin/documents/{document_id}/retry-ocr` 실행 시:
     - OCR 텍스트 캐시를 저장한다.
     - 계약 필드 추출 결과도 함께 갱신한다.

### 업로드 흐름 변경사항
- 기존 업로드/OCR 성공 후 다음 작업을 추가했다.
  - OCR 원문 텍스트를 artifact로 저장
  - 계약 필드 추출 실행
  - 추출 결과 JSON 저장
- 계약 필드 캐시 저장 중 예외가 발생해도 업로드 자체가 실패하지 않도록 로그만 남기고 기존 응답 흐름은 유지한다.

### 기존 구조와의 분리
- `extract_service.py`
  - 기존 역할 유지: OCR/PDF/이미지 텍스트 추출
- `contract_extract_service.py`
  - 신규 역할: OCR 결과 텍스트에서 계약 핵심 정보 추출
- `storage_service.py`
  - 신규 역할 추가: OCR 텍스트와 계약 필드 추출 artifact 저장/조회
- `analysis_service.py`
  - 이번 작업에서는 직접 변경하지 않았다.
  - 추후 `ExtractedContractInfo`를 입력으로 위험 분석을 수행하도록 연결 가능하다.

### 변경 파일 목록
- `FastAPI/backend/app/schemas/contract_extract_schema.py`
- `FastAPI/backend/app/services/contract_extract_service.py`
- `FastAPI/backend/app/services/storage_service.py`
- `FastAPI/backend/app/routers/upload_router.py`
- `FastAPI/backend/app/routers/admin_router.py`

### 검증 결과
- `python -m compileall app` 통과
- `git diff --check` 통과
- 최초 기능 커밋:
  - `7d9eafb feat: add contract field extraction API`

### 향후 확장 포인트
1. 추출 결과 DB 영속 저장
   - 현재는 파일 artifact 기반이다.
   - 추후 `contract_extraction` 테이블 또는 JSON 컬럼으로 이전 가능하다.

2. 위험 분석 서비스 연결
   - `analysis_service.py`에서 `ExtractedContractInfo`를 읽어 위험 규칙을 적용할 수 있다.
   - 예: 보증금 규모, 임대차 기간, 확정일자/전입신고 상태, 선순위 권리 여부 기반 위험 점수화

3. Clova 또는 LLM 기반 보정
   - rule-based 추출 결과를 1차 후보로 사용하고, 낮은 confidence 또는 missing field만 외부 AI 분석으로 보정하는 구조로 확장 가능하다.

4. 정규식 및 한국어 금액 표현 개선
   - 현재는 1차 rule-based 구현이다.
   - OCR 오인식 패턴, 주소 라벨 다양성, 이름/특약 경계 인식은 실제 샘플 축적 후 보강하면 된다.
