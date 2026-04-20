from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SocialProvider(str, Enum):
    kakao = "kakao"
    naver = "naver"
    google = "google"
    apple = "apple"


@dataclass(slots=True)
class UserAccount:
    user_id: str
    email: str
    provider: SocialProvider
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
