from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organization import (
    Organization,
    OrganizationCreate,
    MemberAssignment,
)
from app.database import get_db, OrganizationDB
from app.services.authorization_service import authz_service

router = APIRouter()


@router.get("/", response_model=List[Organization])
async def list_organizations(
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations where the user has at least member access."""
    # Get all organizations from database
    result = await db.execute(select(OrganizationDB))
    all_orgs = result.scalars().all()

    accessible_orgs = []
    for org in all_orgs:
        if authz_service.check_permission_on_org(
            user_id, "can_view_member", org.id
        ):
            accessible_orgs.append(
                Organization(
                    id=org.id,
                    name=org.name,
                    description=org.description,
                    created_at=org.created_at,
                )
            )
    return accessible_orgs


@router.get("/{organization_id}", response_model=Organization)
async def get_organization(
    organization_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific organization."""
    if not authz_service.check_permission_on_org(
        user_id, "can_view_member", organization_id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(OrganizationDB).where(OrganizationDB.id == organization_id)
    )
    org_db = result.scalar_one_or_none()

    if not org_db:
        raise HTTPException(status_code=404, detail="Organization not found")

    return Organization(
        id=org_db.id,
        name=org_db.name,
        description=org_db.description,
        created_at=org_db.created_at,
    )


@router.post("/", response_model=Organization)
async def create_organization(
    organization: OrganizationCreate,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization. Creator becomes admin."""
    org_id = str(uuid.uuid4())

    # Create organization in database
    org_db = OrganizationDB(
        id=org_id,
        name=organization.name,
        description=organization.description,
        created_at=datetime.now(),
    )

    db.add(org_db)
    await db.commit()
    await db.refresh(org_db)

    # Assign creator as admin
    authz_service.assign_user_to_organization(user_id, org_id, "admin")

    return Organization(
        id=org_db.id,
        name=org_db.name,
        description=org_db.description,
        created_at=org_db.created_at,
    )


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Delete an organization (admin only)."""
    if not authz_service.check_permission_on_org(
        user_id, "can_delete_member", organization_id
    ):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(OrganizationDB).where(OrganizationDB.id == organization_id)
    )
    org_db = result.scalar_one_or_none()

    if not org_db:
        raise HTTPException(status_code=404, detail="Organization not found")

    await db.delete(org_db)
    await db.commit()

    return {"message": "Organization deleted successfully"}


@router.post("/{organization_id}/members")
async def add_member(
    organization_id: str,
    member: MemberAssignment,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Add a member to an organization (admin only)."""
    if not authz_service.check_permission_on_org(
        user_id, "can_add_member", organization_id
    ):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if organization exists in database
    result = await db.execute(
        select(OrganizationDB).where(OrganizationDB.id == organization_id)
    )
    org_db = result.scalar_one_or_none()

    if not org_db:
        raise HTTPException(status_code=404, detail="Organization not found")

    if member.role not in ["admin", "member"]:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'member'")

    success = authz_service.assign_user_to_organization(
        member.user_id, organization_id, member.role
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to assign role")

    return {"message": f"User {member.user_id} added as {member.role}"}


@router.delete("/{organization_id}/members/{member_user_id}")
async def remove_member(
    organization_id: str,
    member_user_id: str,
    role: str = Query(..., description="Role to remove ('admin' or 'member')"),
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from an organization (admin only)."""
    if not authz_service.check_permission_on_org(
        user_id, "can_delete_member", organization_id
    ):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if organization exists in database
    result = await db.execute(
        select(OrganizationDB).where(OrganizationDB.id == organization_id)
    )
    org_db = result.scalar_one_or_none()

    if not org_db:
        raise HTTPException(status_code=404, detail="Organization not found")

    if role not in ["admin", "member"]:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'member'")

    success = authz_service.remove_user_from_organization(
        member_user_id, organization_id, role
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove role")

    return {"message": f"User {member_user_id} removed from {role} role"}
