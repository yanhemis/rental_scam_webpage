# 2026-04-20 Update Readme

## 오늘 작업 목표
- PDF 전용 업로드 구조를 모바일 이미지까지 포함하는 방향으로 확장
- OCR/분석 실패 시 추적 가능한 백엔드 구조로 개선
- AWS 연동 전 단계에서 DynamoDB 및 CloudWatch에 붙이기 쉬운 형태로 정리

## 오늘 변경점
1. 업로드 API를 문서 중심 구조로 정리했다.
   - `document_id`, `request_id`, `user_id`, `source`, `status`를 함께 다루도록 변경
   - PDF와 모바일 이미지 업로드 흐름을 같은 문서 단위로 추적 가능하게 정리

2. 문서 메타데이터 구조를 확장했다.
   - `retry_count`
   - `max_retry_count`
   - `last_error`
   - `last_error_at`
   - `next_retry_at`
   - `processing_started_at`
   - `processing_finished_at`
   - `extracted_text_quality`

3. OCR 처리 로직을 강화했다.
   - timeout 추가
   - retry 추가
   - backoff 추가
   - 동시 처리 제한 추가

4. 분석 처리 로직을 강화했다.
   - OCR과 같은 방식으로 timeout, retry, backoff, 동시 처리 제한 구조를 맞춤
   - 현재는 mock 분석이지만 실제 Clova 연동 시 구조 변경이 적도록 준비

5. 로깅 구조를 추가했다.
   - request_id 기반 JSON 로깅 도입
   - 요청 시작/완료/실패 추적 가능
   - 업로드/OCR/분석 이벤트를 같은 request_id로 묶을 수 있게 정리

6. 메트릭 수집 포인트를 추가했다.
   - `UploadSuccessCount`
   - `UploadFailureCount`
   - `OCRSuccessCount`
   - `OCRFailureCount`
   - `OCRRetryCount`
   - `AnalysisSuccessCount`
   - `AnalysisFailureCount`
   - `AnalysisRetryCount`

7. 저장소 구조를 DynamoDB 준비 형태로 정리했다.
   - 현재 저장은 인메모리
   - 하지만 sync payload는 DynamoDB의 `pk/sk/gsi1pk/gsi1sk` 형태로 생성되도록 정리

## 오늘 개선된 점
- 단순 업로드 기능에서 운영 가능한 문서 처리 구조로 발전
- 실패 이력과 재시도 횟수를 문서 기준으로 확인 가능
- 대량 요청 대비를 위한 timeout / concurrency limit / retry 구조 확보
- AWS 서버 팀이 나중에 붙이기 쉬운 데이터 형태 확보
- 향후 CloudWatch, DynamoDB, Clova API 연동을 위한 백엔드 준비 완료

## 현재 기준 성과
- PDF + 이미지 업로드 지원 구조 확보
- 문서 메타데이터 조회/수정/동기화 payload 확인 가능
- request_id 기준 장애 추적 가능
- retry_count 기준 문제 분석 가능
- 분석 단계와 OCR 단계를 분리해 확장성 확보

## 아직 남은 작업
1. 인메모리 저장소를 실제 DynamoDB SDK 호출로 교체
2. mock 분석을 실제 Clova API 호출로 교체
3. metric hook를 실제 CloudWatch 전송으로 연결
4. AWS 콘솔에서 알람 규칙 설정
5. 표준 계약서 diff와 독소조항 리포트 로직 고도화

## 발표용 핵심 메시지
- 오늘은 기능 추가보다 운영 안정성과 확장성을 먼저 확보했다.
- 모바일 업로드를 고려해 OCR/분석 실패에 대응할 수 있는 구조를 만들었다.
- 서버 인프라를 직접 수정하지 않아도 AWS 연동이 가능한 형태로 백엔드를 정리했다.
