import uuid
from datetime import datetime
from typing import Optional

from app.database import AsyncSessionLocal, ResourceDB
from app.models.resource import Resource


async def create_resource(
    name: str,
    resource_type: str,
    organization_id: str,
    description: Optional[str] = None,
) -> Resource:
    """
    Create a resource in the database and link it to an organization in OpenFGA.

    Args:
        name: Name of the resource
        resource_type: Type of resource (e.g., 'database', 'api', 'file')
        organization_id: ID of the organization that owns this resource
        description: Optional description of the resource

    Returns:
        Resource: The created resource object

    Raises:
        Exception: If resource creation or OpenFGA linking fails
    """
    # Generate a unique resource ID
    resource_id = str(uuid.uuid4())

    # Create database session
    async with AsyncSessionLocal() as db:
        try:
            # Create resource in database
            resource_db = ResourceDB(
                id=resource_id,
                name=name,
                description=description,
                resource_type=resource_type,
                organization_id=organization_id,
                created_at=datetime.now(),
            )

            db.add(resource_db)
            await db.commit()
            await db.refresh(resource_db)

            # Link resource to organization in OpenFGA
            from app.services.authorization_service import authz_service
            await authz_service.assign_resource_to_organization(
                resource_id, organization_id
            )

            # Return the created resource
            return Resource(
                id=resource_db.id,
                name=resource_db.name,
                description=resource_db.description,
                resource_type=resource_db.resource_type,
                organization_id=resource_db.organization_id,
                created_at=resource_db.created_at,
            )

        except Exception as e:
            await db.rollback()
            raise Exception(f"Failed to create resource: {e}")
