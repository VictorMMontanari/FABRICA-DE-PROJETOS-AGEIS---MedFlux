from fastapi import APIRouter, File, UploadFile

from app.api.v1.deps import CurrentUser, UserServiceDep
from app.core.constants import AVATAR_MAX_BYTES
from app.schemas.file import FileUploadResponse
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser, users: UserServiceDep) -> UserResponse:
    return users.to_response(user)


@router.put("/me", response_model=UserResponse)
async def update_me(data: UserUpdate, user: CurrentUser, users: UserServiceDep) -> UserResponse:
    return users.to_response(await users.update(user, data))


@router.post("/me/avatar", response_model=FileUploadResponse)
async def upload_avatar(
    user: CurrentUser, users: UserServiceDep, file: UploadFile = File(description="JPEG, PNG ou WEBP até 5 MB")
) -> FileUploadResponse:
    # Lê no máximo o limite + 1 byte: arquivos maiores são recusados sem carregar tudo na memória.
    data = await file.read(AVATAR_MAX_BYTES + 1)
    return await users.update_avatar(user, data)
