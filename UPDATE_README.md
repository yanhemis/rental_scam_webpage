# Update Readme

이 문서는 프로젝트 변경 사항을 날짜별로 순차 기록하기 위한 문서입니다.

## 2026-04-20

### 오늘 작업 목표
- PDF 전용 업로드 구조를 모바일 이미지까지 포함하는 방향으로 확장
- OCR/분석 실패 시 추적 가능한 백엔드 구조로 개선
- AWS 연동 전 단계에서 DynamoDB 및 CloudWatch에 붙이기 쉬운 형태로 정리

### 오늘 변경점
1. 업로드 API를 문서 중심 구조로 정리
   - `document_id`, `request_id`, `user_id`, `source`, `status` 기반으로 흐름 통일
   - PDF와 모바일 이미지 업로드를 같은 문서 단위로 추적 가능하게 변경

2. 문서 메타데이터 구조 확장
   - `retry_count`
   - `max_retry_count`
   - `last_error`
   - `last_error_at`
   - `next_retry_at`
   - `processing_started_at`
   - `processing_finished_at`
   - `extracted_text_quality`

3. OCR 처리 로직 개선
   - timeout 추가
   - retry 추가
   - backoff 추가
   - 동시 처리 제한 추가

4. 분석 처리 로직 개선
   - timeout, retry, backoff, 동시 처리 제한 구조 추가
   - 현재는 mock 분석 기반이지만 실제 Clova 연동 시 구조 변경이 적도록 준비

5. request_id 기반 JSON 로깅 추가
   - 요청 시작/완료/실패 추적 가능
   - 업로드/OCR/분석 이벤트를 같은 request_id로 연결 가능

6. 메트릭 수집 지점 추가
   - `UploadSuccessCount`
   - `UploadFailureCount`
   - `OCRSuccessCount`
   - `OCRFailureCount`
   - `OCRRetryCount`
   - `AnalysisSuccessCount`
   - `AnalysisFailureCount`
   - `AnalysisRetryCount`

7. 저장소 구조를 DynamoDB 준비 형태로 정리
   - 현재 저장은 인메모리 기반
   - sync payload는 DynamoDB `pk/sk/gsi1pk/gsi1sk` 구조로 생성 가능

### 오늘 개선된 점
- 단순 업로드 기능에서 운영 가능한 문서 처리 구조로 발전
- 실패 이력과 재시도 횟수를 문서 기준으로 확인 가능
- 대량 요청 대비를 위한 timeout / concurrency limit / retry 구조 확보
- AWS 서버 연동 시 바로 붙일 수 있는 데이터 형태 확보
- CloudWatch, DynamoDB, Clova API 연동을 위한 백엔드 준비 완료

### 아직 남은 작업
1. 인메모리 저장소를 실제 DynamoDB SDK 호출로 교체
2. mock 분석을 실제 Clova API 호출로 교체
3. metric hook를 실제 CloudWatch 전송으로 연결
4. AWS 콘솔에서 알람 규칙 설정
5. 표준 계약서 diff와 독소조항 리포트 로직 고도화
