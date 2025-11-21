from pydantic import BaseModel


class UploadResponse(BaseModel):
    """
    /api/upload 엔드포인트에서 반환할 응답 데이터 스키마.
    """
    file_name: str      # 업로드된 원본 파일 이름
    file_path: str      # 서버에 저장된 파일 경로 (디버깅/로그용)
    sha256: str         # 파일의 SHA-256 해시값
    text_preview: str   # 추출된 텍스트 일부 (앞부분 미리보기)
    full_text: str      # 전체 추출 텍스트