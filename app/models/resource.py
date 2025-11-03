from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ResourceBase(BaseModel):
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    resource_type: str = Field(
        ..., description="Type of resource (e.g., 'database', 'api', 'file')"
    )


class ResourceCreate(ResourceBase):
    organization_id: str = Field(
        ..., description="Organization that owns this resource"
    )


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    resource_type: Optional[str] = None


class Resource(ResourceBase):
    id: str = Field(..., description="Resource ID")
    organization_id: str = Field(
        ..., description="Organization that owns this resource"
    )
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
