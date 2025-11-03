# ⚙️ Technical Challenges & Solutions  
### JeonseGuard (전세사기 예방 AI 플랫폼)

---

## 📌 목적
이 문서는 개발 과정에서 발견된 **기술적 문제, 에러 로그, 개선 아이디어**를 기록하고  
팀 단위 유지보수 및 회고용으로 활용하기 위해 작성되었습니다.

---

## 🧩 주요 기술적 이슈 & 대응 전략

| 번호 | 구분 | 문제 내용 | 해결 방안 |
|------|------|------------|-------------|
| 1 | PDF / OCR | 문서 인식률 저하, 하이라이트 불일치 | PDF 텍스트 레이어 우선 → OCR 백업(PaddleOCR), 토큰 해시 기반 정합화 |
| 2 | 법률 판단 | 자체 분류기 정확도 낮음 | 법률 판단은 Lawform AI에 위임, 내부는 데이터 전처리·포맷화 전담 |
| 3 | API 연동 | Lawform ↔ GPT 데이터 불일치 | 중간 DTO(JSON) 정의 + Mock JSON 세트로 테스트 |
| 4 | 공공데이터 제약 | 등기·신탁 API 접근 제한 | API 불가 항목은 공식 링크로 유도, 실패 시 UX 유지 |
| 5 | 주소 정규화 | 동일 부동산 중복 조회 | `Juso.go.kr` / Kakao API 기반 표준화, 캐시 Key로 활용 |
| 6 | 위험 점수화 | 초기 데이터 부족 | 점수화 보류 → 카테고리별 위험 레벨로 단순 표시 |
| 7 | 보안정책 | 업로드 파일 저장 리스크 | 업로드 즉시 Lawform 전송, 전송 완료 후 자동삭제 |
| 8 | 비용 문제 | LLM/API 호출비 과다 | 규칙엔진으로 1차 필터 → 의심 문서만 Lawform 전송 |
| 9 | 테스트 비용 | 실제 호출 테스트 어려움 | Mock API / 로컬 LLM(Llama2, Mistral)로 대체 |
| 10 | 환각·정확도 | GPT 결과 불일치 | “출력은 JSON만” 프롬프트 강제 + 검증 파이프라인 |

---

## 🧱 실무에서 적용 중인 알고리즘 / 기술

- **OCR/텍스트 추출:** PaddleOCR, PDFMiner, LayoutLMv3  
- **문장-좌표 매핑:** 토큰 해시 + Smith–Waterman 정렬  
- **리스크 탐지:** Regex 기반 규칙엔진 + Lawform 결과 필터  
- **보안 처리:** AES256 + TLS + Ephemeral File Handling  
- **LLM 포맷 검증:** JSON Schema Validation + Auto-Retry  

---

## 🧠 비용 절감 및 테스트 전략

| 항목 | 절감 방법 |
|------|-----------|
| Lawform 호출비 | Mock JSON으로 사전테스트 |
| GPT 비용 | 로컬 모델(Llama2/Mistral) 사용 |
| OCR 실패율 | 이미지 전처리 자동화 |
| API 제한 | 캐시·재시도·Fallback 설계 |
| 사용자 테스트 | 소규모 테스터 그룹 운영 |

---

## 🧰 개발자 참고 로그

- **오류 유형별 폴더:** `/logs/errors/YYYY-MM/`  
- **실패 케이스 기록 형식:**  
[Error ID]
Type: OCR_MISMATCH
File: contract_05.pdf
Description: 텍스트 레이어 손상 → OCR fallback 성공
Action: 개선된 OCR 모델 학습 필요

yaml
코드 복사
- **성공률 지표:**  
- OCR 인식률 90% 이상  
- Lawform–GPT 데이터 정합률 95% 이상  
- 삭제 완료 로그 100% 확인

---

## 🧾 향후 개선 예정

- OCR 파이프라인 성능 향상 (LayoutLMv3 fine-tuning)  
- GPT 결과 자동 검증 (JSON Schema + Key 검증)  
- 공공기관 API 정식 인증 확보  
- 사용자 리포트 시각화 강화 (React Canvas + Tooltip Layer)

---

## 📅 업데이트 내역
| 버전 | 날짜 | 주요 변경점 |
|------|------|--------------|
| v1.0 | 2025-10 | 초기 기술문제 및 해결방안 정리 |
| v1.1 | 예정 | 실제 테스트 결과 반영 및 개선내역 추가 |

---

**Author:** codec  
**Project:** 전세사기 예방 AI 플랫폼 (JeonseGuard)  
**License:** MIT  
