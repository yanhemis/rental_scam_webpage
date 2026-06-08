# Standard PDF Structure Notes

Source reference:

- [주택임대차 표준계약서(원본 게시용) (1).pdf](C:/Users/USER/Downloads/주택임대차%20표준계약서(원본%20게시용)%20(1).pdf:1)

This note summarizes the text structure extracted from the source PDF and the exact sections that the test template should preserve.

## Page 1 core structure

Top title:

- `주택임대차표준계약서`

Immediately visible standard clauses near the top:

- `제2조(임대차기간)`
- `제3조(입주 전 수리)`
- `제4조(임차주택의 사용·관리·수선)`

Main block order:

1. `[임차주택의 표시]`
2. `계약의종류`
3. `미납 국세·지방세`
4. `선순위 확정일자 현황`
5. `확정일자 부여란`
6. `[계약내용]`
7. `제1조(보증금과 차임 및 관리비)`
8. `수리 필요 시설 / 수리 완료 시기 / 미수리 시 처리 방식`
9. `q보증금 있는 월세 / q전세 / q월세`
10. `임대인부담 / 임차인부담`

Important literal guidance text that should remain recognizable:

- `주택임대차계약서를 제출하고 임대차 신고의 접수를 완료한 경우에는 별도로 확정일자 부여를 신청할 필요가 없습니다.`
- `이 계약서는 법무부가 국토교통부·서울시 및 관련 전문가들과 함께 ... 관계법령에 근거하여 만들었습니다.`

## Page 2 core structure

Standard clauses sequence:

- `제5조(계약의 해제)`
- `제6조(채무불이행과 손해배상)`
- `제7조(계약의 해지)`
- `제8조(갱신요구와 거절)`
- `제9조(계약의 종료)`
- `제10조(비용의 정산)`
- `제11조(분쟁의 해결)`
- `제12조(중개보수 등)`
- `제13조(중개대상물확인·설명서 교부)`

Special terms area starts with:

- `[특약사항]`

Representative default special-term flow from the PDF:

- 전입신고와 확정일자 약정
- 약정일 다음날까지 담보권 설정 금지
- 위반 시 해제 또는 해지 및 손해배상
- 선순위 임대차 정보 / 미납·체납 국세·지방세 관련 해제권
- 분쟁조정위원회 조정 동의 여부
- 철거 또는 재건축 계획 여부
- 상세주소 부여 신청 동의 여부

## Page 3 signature structure

Signature parties:

- `임대인`
- `임차인`
- `개업공인중개사`

Fields repeated in the signature area:

- 주소
- 주민등록번호
- 전화
- 성명
- 대리인
- 사무소소재지
- 사무소명칭
- 대표
- 등록번호
- 소속공인중개사

## Template alignment decisions

The template should:

- Preserve section order above
- Keep headings close to the source wording
- Allow placeholder-driven sample generation
- Be OCR-friendly rather than visually identical to the official form
- Include enough signature metadata for entity extraction tests
