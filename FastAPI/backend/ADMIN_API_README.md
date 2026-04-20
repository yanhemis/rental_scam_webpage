# Admin API Readme

프론트엔드 관리자 페이지 연동을 위한 관리자용 API 요약 문서입니다.

## 기준 정보
- Base URL: `/api/admin`
- 현재 관리자 API는 문서 목록, 상세 조회, 요약 대시보드, OCR 재처리, 분석 재처리를 지원합니다.

## 1. 관리자 문서 목록 조회

### Request
- Method: `GET`
- URL: `/api/admin/documents`

### Query Parameters
- `status`
- `analysis_status`
- `has_error`
- `source`
- `user_id`

### Response
```json
{
  "items": [
    {
      "document_id": "doc-1234567890ab",
      "request_id": "req-1234567890abcdef",
      "user_id": "user-001",
      "file_name": "contract_sample.pdf",
      "file_path": "C:/.../uploads/contract_sample.pdf",
      "sha256": "abc123...",
      "content_type": "application/pdf",
      "source": "pdf",
      "status": "text_extracted",
      "ocr_engine": "pytesseract",
      "analysis_provider": "clova-mock",
      "analysis_status": "pending",
      "report_status": "pending",
      "retry_count": 1,
      "max_retry_count": 3,
      "last_error": null,
      "last_error_at": null,
      "next_retry_at": null,
      "processing_started_at": "2026-04-21T00:30:00",
      "processing_finished_at": "2026-04-21T00:30:04",
      "extracted_text_quality": 0.91,
      "deletion_scheduled_at": "2026-04-22T00:30:00",
      "created_at": "2026-04-21T00:29:58",
      "updated_at": "2026-04-21T00:30:04"
    }
  ],
  "total": 1
}
```

### 목록 화면 추천 컬럼
- `document_id`
- `file_name`
- `source`
- `status`
- `analysis_status`
- `retry_count`
- `extracted_text_quality`
- `last_error`
- `created_at`

## 2. 관리자 문서 상세 조회

### Request
- Method: `GET`
- URL: `/api/admin/documents/{document_id}`

### Response
- 문서 메타데이터 단건 전체 반환

### 상세 화면 추천 섹션
- 기본 정보
  - `document_id`
  - `request_id`
  - `user_id`
  - `file_name`
  - `content_type`
  - `source`
- 처리 상태
  - `status`
  - `analysis_status`
  - `report_status`
- 품질 정보
  - `ocr_engine`
  - `analysis_provider`
  - `extracted_text_quality`
- 장애 정보
  - `retry_count`
  - `max_retry_count`
  - `last_error`
  - `last_error_at`
  - `next_retry_at`
- 시간 정보
  - `processing_started_at`
  - `processing_finished_at`
  - `created_at`
  - `updated_at`
  - `deletion_scheduled_at`

## 3. 관리자 대시보드 요약 조회

### Request
- Method: `GET`
- URL: `/api/admin/dashboard/summary`

### Response
```json
{
  "total_documents": 120,
  "uploaded_documents": 12,
  "text_extracted_documents": 60,
  "analysis_pending_documents": 10,
  "analysis_completed_documents": 30,
  "failed_documents": 8,
  "documents_with_errors": 9,
  "documents_scheduled_for_deletion": 100,
  "average_extracted_text_quality": 0.88,
  "total_retry_count": 14
}
```

### 대시보드 카드 추천
- 전체 문서 수
- 현재 업로드 직후 상태 문서 수
- OCR 완료 문서 수
- 분석 대기 문서 수
- 분석 완료 문서 수
- 실패 문서 수
- 오류 문서 수
- 평균 OCR 품질
- 전체 재시도 횟수

## 4. 관리자 OCR 재처리

### Request
- Method: `POST`
- URL: `/api/admin/documents/{document_id}/retry-ocr`

### Response
```json
{
  "document_id": "doc-1234567890ab",
  "action": "retry_ocr",
  "status": "completed",
  "retry_count": 1,
  "message": "OCR 재처리가 완료되었습니다. 추출 길이: 1542"
}
```

### 프론트 사용 권장
- `failed` 상태 문서
- `last_error`가 있는 문서
- OCR 품질이 낮은 문서

## 5. 관리자 분석 재처리

### Request
- Method: `POST`
- URL: `/api/admin/documents/{document_id}/retry-analysis`

### Response
```json
{
  "document_id": "doc-1234567890ab",
  "action": "retry_analysis",
  "status": "completed",
  "retry_count": 0,
  "message": "분석 재처리가 완료되었습니다."
}
```

### 프론트 사용 권장
- `analysis_status=failed`
- 분석 미완료 상태 문서
- 운영자가 수동 재분석이 필요하다고 판단한 문서

## 관리자 페이지 구성 추천

### 1. 문서 목록 화면
- 검색/필터
  - 상태
  - 분석 상태
  - 에러 여부
  - source
  - 사용자 ID
- 주요 컬럼
  - 문서 ID
  - 파일명
  - 상태
  - 분석 상태
  - 재시도 횟수
  - OCR 품질
  - 마지막 오류
  - 생성일

### 2. 문서 상세 화면
- 문서 메타데이터 전체 표시
- OCR 재처리 버튼
- 분석 재처리 버튼

### 3. 운영 대시보드
- 전체 문서 수
- 실패 문서 수
- 오류 문서 수
- 평균 OCR 품질
- 총 재시도 횟수

## 프론트 연동 시 참고
- `last_error`가 `null`이 아니면 오류 상태 배지 표시 권장
- `retry_count > 0` 이면 재시도 이력 표시 권장
- `extracted_text_quality`는 소수점 2자리로 표시 권장
- `deletion_scheduled_at`는 관리자 화면에서 별도 보관/삭제 영역에 노출 권장
