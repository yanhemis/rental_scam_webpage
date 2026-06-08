# Standard Contract Template

이 폴더의 [standard_contract_template.html](/C:/Users/USER/Desktop/FastAPI/backend/test_assets/standard_contract_samples/standard_contract_template.html:1)은
실제 공개된 주택임대차 표준계약서의 섹션 흐름을 참고해 만든 테스트용 템플릿입니다.

목적:

- OCR 테스트용 계약서 원본 제작
- 정보추출 테스트용 표준 양식 통일
- 위험 조항 삽입 위치 표준화

사용 순서:

1. 템플릿의 `{{placeholder}}` 값을 샘플별 데이터로 치환
2. HTML을 브라우저 또는 렌더러로 PDF/PNG 변환
3. 변환된 결과를 OCR 테스트 문서로 사용
4. 모바일 촬영본이 필요하면 후처리로 기울기/그림자/저화질 변형 추가

주요 장점:

- 샘플마다 양식이 흔들리지 않음
- 표준계약서 필드 위치가 일정해 추출 규칙 설계가 쉬움
- 위험 특약만 바꿔도 정상/주의/위험 샘플을 반복 생성 가능

필수 치환 필드는 [standard_contract_template_fields.json](/C:/Users/USER/Desktop/FastAPI/backend/test_assets/standard_contract_samples/standard_contract_template_fields.json:1)에 정리돼 있습니다.
