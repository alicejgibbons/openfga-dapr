from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OrganizationBase(BaseModel):
    name: str = Field(..., description="Organization name")
    description: Optional[str] = Field(None, description="Organization description")


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Organization(OrganizationBase):
    id: str = Field(..., description="Organization ID")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemberAssignment(BaseModel):
    user_id: str = Field(..., description="User ID to assign/remove")
    role: str = Field(..., description="Role: 'admin' or 'member'")
    organization_id: str = Field(..., description="Organization ID")
