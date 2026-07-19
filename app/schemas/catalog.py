from typing import List, Optional

from pydantic import BaseModel


class CatalogRoleOut(BaseModel):
    id: int
    slug: str
    name: str

    model_config = {"from_attributes": True}


class CatalogItemOut(BaseModel):
    id: int
    category: str
    name: str
    description: Optional[str] = None
    provider: Optional[str] = None
    url: Optional[str] = None
    estimated_hours: Optional[int] = None
    steps: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class GroupedItems(BaseModel):
    skill: List[CatalogItemOut] = []
    course: List[CatalogItemOut] = []
    tool: List[CatalogItemOut] = []
    project: List[CatalogItemOut] = []


class RoleSuggestions(BaseModel):
    matched: bool
    label: str
    role: Optional[CatalogRoleOut] = None
    items: GroupedItems
