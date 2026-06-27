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


class ParseItem(BaseModel):
    text_en: str = Field(..., min_length=1, max_length=500)
    text_zh: str | None = Field(default=None, max_length=2000)


class ParseRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=20000)


class ParseResponse(BaseModel):
    items: list[ParseItem]
    split_count: int
    translation_failures: int


class ImportRequest(BaseModel):
    items: list[ParseItem] = Field(..., min_length=1, max_length=500)
    source: str = Field(default="parser", max_length=64)


class ImportResponse(BaseModel):
    saved: int
    incremented: int
    tag_failures: int
    items: list[LibraryItem]


class LoraConfigOut(BaseModel):
    folder_path: str | None = None
    updated_at: datetime | None = None


class LoraConfigUpdate(BaseModel):
    folder_path: str | None = Field(default=None, max_length=1024)


class LoraMeta(BaseModel):
    base_model: str | None = None
    trigger_words: str | None = None
    network_module: str | None = None
    description: str | None = None
    author: str | None = None


class TriggerGroup(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    words: list[str] = Field(default_factory=list, max_length=50)


class LoraItem(BaseModel):
    file_path: str
    file_name: str
    file_size: int
    file_mtime: datetime | None = None
    meta: LoraMeta
    nickname: str | None = None
    rating: int = 0
    comment: str | None = None
    lora_type: str | None = None
    trigger_words_user: str | None = None
    trigger_groups: list[TriggerGroup] = Field(default_factory=list)
    has_meta: bool = False
    updated_at: datetime | None = None


class LoraListResponse(BaseModel):
    folder_path: str | None = None
    items: list[LoraItem]
    total: int


class LoraEntryUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=255)
    rating: int | None = Field(default=None, ge=0, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    lora_type: str | None = Field(default=None, max_length=64)
    trigger_words_user: str | None = Field(default=None, max_length=8000)
    trigger_groups: list[TriggerGroup] | None = None


TagTreeNode.model_rebuild()