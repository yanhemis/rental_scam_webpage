from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services import file_service, extract_service
from app.schemas.upload_schema import UploadResponse

# 전역 라우터 객체 생성 (main.py에서 이걸 include_router로 연결)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_contract(file: UploadFile = File(...)):
    """
    전세계약서 PDF 파일을 업로드하고 텍스트를 추출해 반환하는 엔드포인트.
    """
    # 1. 파일 타입 검증
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF 파일만 업로드 가능합니다.",
        )

    # 2. 파일 저장 + SHA-256 해시 계산
    saved_path, sha256_hash = await file_service.save_upload_file(file)

    # 3. 저장된 PDF에서 텍스트 추출
    extracted_text = extract_service.extract_text_from_pdf(saved_path)

    # 4. 미리보기용 텍스트 (앞 500자)
    preview_text = extracted_text[:500] if extracted_text else ""

    # 5. 응답 스키마에 맞춰 반환
    return UploadResponse(
        file_name=file.filename,
        file_path=str(saved_path),
        sha256=sha256_hash,
        text_preview=preview_text,
        full_text=extracted_text,
    )