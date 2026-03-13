from pydantic import BaseModel


class SettingsResponse(BaseModel):
    github_username: str = ""
    auto_summarize: bool = True
    include_readmes: bool = True
    first_name: str = ""
    last_name: str = ""
    email: str = ""


class SettingsUpdate(BaseModel):
    github_username: str | None = None
    auto_summarize: bool | None = None
    include_readmes: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
