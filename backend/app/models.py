from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


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