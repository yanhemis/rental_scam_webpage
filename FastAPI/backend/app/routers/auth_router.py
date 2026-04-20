from uuid import uuid4

from fastapi import APIRouter

from app.schemas.user_schema import SocialLoginRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/social-login", response_model=UserResponse)
async def social_login(payload: SocialLoginRequest):
    return UserResponse(
        user_id=f"user-{uuid4().hex[:12]}",
        email=f"{payload.provider.value}_user@example.com",
        provider=payload.provider,
        is_active=True,
    )
