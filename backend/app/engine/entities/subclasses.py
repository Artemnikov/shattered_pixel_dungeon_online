from typing import Dict, Optional, List

from pydantic import BaseModel, Field


class Subclass:
    WARDEN = "warden"


class TalentInfo(BaseModel):
    talents: Dict[str, int] = Field(default_factory=dict)

    def has(self, name: str) -> bool:
        return self.talents.get(name, 0) > 0

    def level(self, name: str) -> int:
        return self.talents.get(name, 0)


class SubclassInfo(BaseModel):
    subclass: Optional[str] = None
    talent_info: TalentInfo = Field(default_factory=TalentInfo)
