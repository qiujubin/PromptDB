from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    system_prompt: str = Field(..., min_length=1, max_length=8000)
    user_input: str = Field(..., min_length=1, max_length=8000)


class GenerateResponse(BaseModel):
    text: str


class SaveRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=20000)
    source: str = Field(default="manual", max_length=64)
    text_zh: str | None = Field(default=None, max_length=8000)


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None = None


class TagTreeNode(TagOut):
    usage_count: int = 0
    children: list["TagTreeNode"] = []


class LibraryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text_en: str
    text_zh: str | None = None
    usage_count: int
    source: str | None = None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None
    tags: list[TagOut] = []


class SaveResponse(BaseModel):
    saved: int
    incremented: int
    failed_translations: int
    tag_failures: int = 0
    items: list[LibraryItem]
    record_id: int | None = None


class LibraryResponse(BaseModel):
    items: list[LibraryItem]
    total: int
    page: int
    page_size: int


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    parent_id: int | None = None


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    parent_id: int | None = None


class PromptTagsUpdate(BaseModel):
    tag_ids: list[int] = Field(default_factory=list, max_length=50)


class BulkAutoTagResponse(BaseModel):
    scanned: int
    tagged: int
    failed: int


class GenerationRecordImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    position: int
    url: str | None = None
    created_at: datetime


class GenerationRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    text_zh: str | None = None
    text_en: str | None = None
    rating: int
    comment: str | None = None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    images: list[GenerationRecordImageOut] = []
    prompts: list[LibraryItem] = []


class GenerationRecordListResponse(BaseModel):
    items: list[GenerationRecordOut]
    total: int
    page: int
    page_size: int


class GenerationRecordUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    text_zh: str | None = Field(default=None, max_length=8000)
    text_en: str | None = Field(default=None, max_length=20000)
    rating: int | None = Field(default=None, ge=0, le=5)
    comment: str | None = Field(default=None, max_length=1000)
    is_favorite: bool | None = None


class ImageOrderUpdate(BaseModel):
    image_ids: list[int] = Field(..., min_length=1, max_length=50)


TagTreeNode.model_rebuild()