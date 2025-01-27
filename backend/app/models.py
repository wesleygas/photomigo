from sqlmodel import Field, SQLModel
from datetime import datetime, timezone

class Group(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    album_url: str
    album_id: str
    current_asset: int
    last_rollover: datetime = Field(nullable=False)
    last_skip_request: datetime = Field(nullable=False)

class Device(SQLModel, table=True):
    id: str | None = Field(default=None, primary_key=True)
    group_id: int | None = Field(default=None, foreign_key="group.id")
