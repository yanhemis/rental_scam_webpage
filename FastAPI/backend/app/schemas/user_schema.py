from enum import Enum

from pydantic import BaseModel


class SocialProviderType(str, Enum):
    kakao = "kakao"
    naver = "naver"
    google = "google"
    apple = "apple"


class SocialLoginRequest(BaseModel):
    provider: SocialProviderType
    access_token: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    provider: SocialProviderType
    is_active: bool = True
