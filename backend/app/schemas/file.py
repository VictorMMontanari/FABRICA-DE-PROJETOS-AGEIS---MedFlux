from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    bucket: str
    object_name: str
    content_type: str
    size: int
    url: str
    expires_in: int
