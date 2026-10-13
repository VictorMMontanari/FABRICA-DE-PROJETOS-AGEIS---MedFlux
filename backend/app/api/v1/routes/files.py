from fastapi import APIRouter, Response

from app.api.v1.deps import CurrentUser, StorageServiceDep

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{bucket}/{object_name:path}", response_class=Response)
async def get_file(bucket: str, object_name: str, user: CurrentUser, storage: StorageServiceDep) -> Response:
    """Baixa um arquivo do próprio usuário pelo backend (alternativa à URL pré-assinada).

    ponytail: o conteúdo é lido inteiro na memória; ok para avatares (≤5 MB) e transcrições.
    Para documentos grandes, trocar por StreamingResponse.
    """
    stored = await storage.get_user_file(user.id, bucket, object_name)
    return Response(
        content=stored.data,
        media_type=stored.content_type,
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )
