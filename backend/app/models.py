from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


generation_record_prompts = Table(
    "generation_record_prompts",
    Base.metadata,
    Column(
        "record_id",
        Integer,
        ForeignKey("generation_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "prompt_id",
        Integer,
        ForeignKey("prompts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
)


class Prompt(Base):
    __tablename__ = "prompts"
    __table_args__ = (
        Index(
            "uq_prompts_text_en_lower",
            text("lower(text_en)"),
            unique=True,
        ),
        Index("ix_prompts_usage_count", text("usage_count DESC")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary="prompt_tags",
        back_populates="prompts",
        lazy="selectin",
    )

    records: Mapped[list["GenerationRecord"]] = relationship(
        secondary="generation_record_prompts",
        back_populates="prompts",
    )


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (Index("uq_tag_parent_name", "parent_id", "name", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prompts: Mapped[list[Prompt]] = relationship(
        secondary="prompt_tags",
        back_populates="tags",
    )


class PromptTag(Base):
    __tablename__ = "prompt_tags"

    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GenerationRecord(Base):
    __tablename__ = "generation_records"
    __table_args__ = (
        Index("ix_grec_is_favorite", "is_favorite"),
        Index("ix_grec_created_at", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    images: Mapped[list["GenerationRecordImage"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        order_by="GenerationRecordImage.position",
        lazy="selectin",
    )
    prompts: Mapped[list["Prompt"]] = relationship(
        secondary="generation_record_prompts",
        back_populates="records",
        lazy="selectin",
    )


class GenerationRecordImage(Base):
    __tablename__ = "generation_record_images"
    __table_args__ = (Index("ix_grec_img_record_pos", "record_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("generation_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    record: Mapped["GenerationRecord"] = relationship(back_populates="images")


class LoraConfig(Base):
    __tablename__ = "lora_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    folder_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LoraEntry(Base):
    __tablename__ = "lora_entries"

    file_path: Mapped[str] = mapped_column(String(1024), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_mtime: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    base_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trigger_words: Mapped[str | None] = mapped_column(Text, nullable=True)
    network_module: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)

    nickname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    lora_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    trigger_words_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_groups: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )