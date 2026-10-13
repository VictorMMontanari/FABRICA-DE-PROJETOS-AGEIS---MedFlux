from fastapi import APIRouter, status

from app.api.v1.deps import AuthServiceDep, CurrentUser, UserServiceDep
from app.schemas.auth import TokenResponse, UserCreate, UserLogin
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, auth: AuthServiceDep, users: UserServiceDep) -> TokenResponse:
    """Cria a conta e já devolve a sessão (mesmo formato do login)."""
    user = await auth.register(data)
    token, expires_in = auth.issue_token(user)
    return TokenResponse(token=token, expires_in=expires_in, user=users.to_response(user))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, auth: AuthServiceDep, users: UserServiceDep) -> TokenResponse:
    user = await auth.authenticate(data)
    token, expires_in = auth.issue_token(user)
    return TokenResponse(token=token, expires_in=expires_in, user=users.to_response(user))


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser, users: UserServiceDep) -> UserResponse:
    return users.to_response(user)
