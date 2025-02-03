from sqlmodel import Field, SQLModel
from datetime import datetime

class Group(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    album_url: str
    album_id: str
    current_asset: int
    last_rollover: datetime = Field(nullable=False)
    last_skip_request: datetime = Field(nullable=False)
    random_seed: int = Field(nullable=False, default=0)
    rollover_delay_minutes: int = Field(nullable=False, default=5)

class Device(SQLModel, table=True):
    id: str | None = Field(default=None, primary_key=True)
    group_id: int | None = Field(default=None, foreign_key="group.id")
    owner: str | None = Field(default=None)
    last_request: datetime | None

class LoginRequest(SQLModel, table=True):
    __tablename__ = "login_request"
    device_id: str = Field(primary_key=True, foreign_key="device.id")
    request_timestamp: datetime
