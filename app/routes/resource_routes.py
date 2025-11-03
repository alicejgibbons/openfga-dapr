from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.resource import Resource, ResourceCreate
from app.database import get_db, ResourceDB
from app.services.authorization_service import authz_service

router = APIRouter()


@router.get("/", response_model=List[Resource])
async def list_resources(
    user_id: str = Query(..., description="User ID for authorization"),
    organization_id: str = Query(None, description="Filter by organization"),
    db: AsyncSession = Depends(get_db),
):
    """List all resources the user can view."""
    # Build query
    query = select(ResourceDB)
    if organization_id:
        query = query.where(ResourceDB.organization_id == organization_id)

    result = await db.execute(query)
    all_resources = result.scalars().all()

    accessible_resources = []
    for resource in all_resources:
        if await authz_service.check_permission_on_resource(
            user_id, "can_view_resource", resource.id
        ):
            accessible_resources.append(
                Resource(
                    id=resource.id,
                    name=resource.name,
                    description=resource.description,
                    resource_type=resource.resource_type,
                    organization_id=resource.organization_id,
                    created_at=resource.created_at,
                )
            )

    return accessible_resources


@router.get("/{resource_id}", response_model=Resource)
async def get_resource(
    resource_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific resource."""
    if not await authz_service.check_permission_on_resource(
        user_id, "can_view_resource", resource_id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(select(ResourceDB).where(ResourceDB.id == resource_id))
    resource_db = result.scalar_one_or_none()

    if not resource_db:
        raise HTTPException(status_code=404, detail="Resource not found")

    return Resource(
        id=resource_db.id,
        name=resource_db.name,
        description=resource_db.description,
        resource_type=resource_db.resource_type,
        organization_id=resource_db.organization_id,
        created_at=resource_db.created_at,
    )


@router.post("/", response_model=Resource)
async def create_resource(
    resource: ResourceCreate,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new resource (admin or member of organization)."""
    if not await authz_service.check_permission_on_org(
        user_id, "can_add_resource", resource.organization_id
    ):
        raise HTTPException(
            status_code=403, detail="Cannot add resources to this organization"
        )

    resource_id = str(uuid.uuid4())

    # Create resource in database
    resource_db = ResourceDB(
        id=resource_id,
        name=resource.name,
        description=resource.description,
        resource_type=resource.resource_type,
        organization_id=resource.organization_id,
        created_at=datetime.now(),
    )

    db.add(resource_db)
    await db.commit()
    await db.refresh(resource_db)

    # Link resource to organization in OpenFGA
    await authz_service.assign_resource_to_organization(
        resource_id, resource.organization_id
    )

    return Resource(
        id=resource_db.id,
        name=resource_db.name,
        description=resource_db.description,
        resource_type=resource_db.resource_type,
        organization_id=resource_db.organization_id,
        created_at=resource_db.created_at,
    )


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a resource (admin only)."""
    if not await authz_service.check_permission_on_resource(
        user_id, "can_delete_resource", resource_id
    ):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(ResourceDB).where(ResourceDB.id == resource_id))
    resource_db = result.scalar_one_or_none()

    if not resource_db:
        raise HTTPException(status_code=404, detail="Resource not found")

    await db.delete(resource_db)
    await db.commit()

    return {"message": "Resource deleted successfully"}


@router.get("/{resource_id}/permissions")
async def check_resource_permissions(
    resource_id: str,
    user_id: str = Query(..., description="User ID to check permissions for"),
    db: AsyncSession = Depends(get_db),
):
    """Check what permissions a user has on a specific resource."""
    result = await db.execute(select(ResourceDB).where(ResourceDB.id == resource_id))
    resource_db = result.scalar_one_or_none()

    if not resource_db:
        raise HTTPException(status_code=404, detail="Resource not found")

    permissions = {
        "can_view": await authz_service.check_permission_on_resource(
            user_id, "can_view_resource", resource_id
        ),
        "can_delete": await authz_service.check_permission_on_resource(
            user_id, "can_delete_resource", resource_id
        ),
    }

    return {"resource_id": resource_id, "user_id": user_id, "permissions": permissions}
