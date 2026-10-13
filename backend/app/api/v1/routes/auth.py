from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError

from app.api.v1.deps import AuthServiceDep, CurrentUser, UserServiceDep
from app.core.exceptions import UnauthorizedError
from app.schemas.auth import OAuthTokenResponse, TokenResponse, UserCreate, UserLogin
from app.schemas.common import error_responses
from app.schemas.user import UserResponse
from app.services.auth_service import INVALID_CREDENTIALS

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário",
    responses=error_responses(409, 422),
)
async def register(data: UserCreate, auth: AuthServiceDep, users: UserServiceDep) -> TokenResponse:
    """Cria a conta e já devolve a sessão (mesmo formato do login).

    Regras: nome com 2+ letras, email válido e único, senha com 6 a 72 bytes.
    """
    user = await auth.register(data)
    token, expires_in = auth.issue_token(user)
    return TokenResponse(token=token, expires_in=expires_in, user=users.to_response(user))


@router.post("/login", response_model=TokenResponse, summary="Login (JSON)", responses=error_responses(401, 422, 429))
async def login(data: UserLogin, auth: AuthServiceDep, users: UserServiceDep) -> TokenResponse:
    """Login usado pelo frontend. Copie o `token` da resposta para usar em outros clientes."""
    user = await auth.authenticate(data)
    token, expires_in = auth.issue_token(user)
    return TokenResponse(token=token, expires_in=expires_in, user=users.to_response(user))


@router.post(
    "/token",
    response_model=OAuthTokenResponse,
    summary="Login OAuth2 (formulário, usado pelo Swagger)",
    responses=error_responses(401, 429),
)
async def token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], auth: AuthServiceDep
) -> OAuthTokenResponse:
    """Mesmo login, no formato OAuth2 password flow (`username` = email).

    É o endpoint chamado pelo botão **Authorize** do Swagger.
    """
    try:
        credentials = UserLogin(email=form.username, password=form.password)
    except ValidationError as exc:
        raise UnauthorizedError(INVALID_CREDENTIALS, code="invalid_credentials") from exc
    user = await auth.authenticate(credentials)
    access_token, expires_in = auth.issue_token(user)
    return OAuthTokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse, summary="Usuário autenticado", responses=error_responses(401))
async def me(user: CurrentUser, users: UserServiceDep) -> UserResponse:
    return users.to_response(user)
