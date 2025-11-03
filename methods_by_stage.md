1️⃣ 업로드·검증 단계

✅ S3 Presigned PUT + SHA-256 무결성 검증

장점: 서버 부하↓, 대용량 업로드 가능, 권한 및 만료 제어 용이

단점: presign·만료 플로우 설계 필요

✅ 파일 형식 검증: python-magic(매직넘버) + MIME 화이트리스트

장점: 확장자 위조 방지

단점: OS별 라이브러리 의존성 존재

✅ AV 스캔: S3 이벤트 → Lambda + ClamAV

장점: 악성 문서 업로드 차단

단점: Lambda 레이어·업데이트 관리 필요

2️⃣ PDF 텍스트 추출 (텍스트 기반)

✅ PyMuPDF(fitz)

장점: 빠름, 글자/단어/스팬 좌표 추출로 하이라이트 매핑 용이

단점: 문단 재구성 로직 보완 필요

⚙️ pdfplumber

장점: 표·레이아웃 추출에 강함

단점: 상대적으로 느림, 메모리 사용량↑

⚙️ pdfminer.six

장점: 세밀한 제어 가능

단점: 구현 복잡, 좌표 관리 불편

추천 조합: PyMuPDF로 기본 텍스트+좌표 추출, 표 구간만 pdfplumber 보조.

3️⃣ OCR (스캔본)

✅ Tesseract (ko+eng) + OpenCV 전처리(이진화, 데스큐)

장점: 무료, 오프라인 동작, 한글 지원

단점: 품질 튜닝 필요, 표·세로쓰기 인식 약함

⚙️ PaddleOCR

장점: 한글 인식률·속도 우수

단점: 모델 크기 큼, GPU 필요

⚙️ AWS Textract

장점: 폼/테이블 인식률 우수

단점: 유료, 개인정보 규제 고려 필요

전략: 문서의 텍스트 비율이 낮을 때 OCR로 폴백.

4️⃣ 레이아웃 분석·조항 분할

✅ PyMuPDF 스팬 병합 + 정규식(예: 제\\s*\\d+\\s*조) 기반 분리

장점: 법률 문서에 강함, 빠름

단점: 비정형 문서에서 조항 누락 가능

⚙️ layoutparser + Detectron2

장점: 시각적 레이아웃 인식으로 정확도↑

단점: 모델 학습·튜닝 비용 높음

5️⃣ 표(Table) 추출

✅ camelot-py

장점: 그리드 기반 표 인식 정확, 제어 쉬움

단점: 환경 의존성 있음 (Ghostscript 필요)

⚙️ tabula-py

장점: 사용 간단, 자바 기반

단점: 정확도·제어 한계

표 추출은 선택 기능 — MVP에서는 텍스트만 처리.

6️⃣ 하이라이트 매핑 (문구 → 좌표)

✅ PyMuPDF page.search_for() / words() 기반 역매핑

장점: 빠르고 스팬 단위 bbox 확보 쉬움

단점: OCR 결과와 혼합 시 좌표 오차 발생 가능

보정 방법: 레벤슈타인 거리 + 주변 문맥 윈도우로 위치 재확인.

7️⃣ 위험 탐지·점수화 (후처리)

✅ 규칙 기반 Rule Engine (키워드·패턴·가중치 JSON) + Lawform 결과 결합

장점: 예측 가능, 일관성, 비용 0원

단점: 커버리지 한계 → Lawform 결과 병합 필요

⚙️ GPT-mini 보정 (선택)

장점: 문장 자연화, 리포트 가독성 향상

단점: 외부 호출 추가 비용 발생

8️⃣ 리포트 생성 (PDF/HTML)

✅ HTML 템플릿 + Playwright PDF 출력

장점: UI 스타일 자유, 화면/파일 일관성 유지

단점: 헤드리스 런타임 필요

⚙️ WeasyPrint

장점: Python 단독 PDF 생성 가능

단점: CSS 기능 제한, 폰트 제약

9️⃣ 웹 미리보기 (PDF.js)

✅ PDF.js (React 래핑)

장점: 안정적, 페이지 탐색·확대 지원

단점: 대용량 문서 초기 로딩 지연 가능

보안: Presigned GET(5–10분), 별도 도메인, Content-Disposition: attachment 권장.

🔟 주소 정규화·공공데이터 (2차 단계)

✅ 규칙·사전 기반 주소 파서 (도로명/지번 구분)

⚙️ 공공 API (국토부/HUG/등기)

캐시: Redis, rate limit, retry 정책 적용

11️⃣ 재분석·버전관리

✅ analyses(version, reasons, lawform_meta) 누적 저장

장점: 개선 이력 관리, 롤백/비교 용이

단점: TTL과 별개로 관리 필요

🧩 단계별 선택 기준 요약
조건	선택 기준
텍스트 PDF	PyMuPDF + pdfplumber 일부
스캔본	Tesseract + OpenCV (Textract 옵션)
하이라이트	PyMuPDF 좌표 우선, OCR 혼합 시 보정
비용/속도 우선	규칙 기반 후처리 + GPT-mini 최소 사용
보안	Presigned, 해시 검증, AV 스캔, TTL 자동삭제
