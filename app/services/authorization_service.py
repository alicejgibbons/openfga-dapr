import logging
from typing import List
from openfga_sdk import OpenFgaClient
from openfga_sdk.client import ClientConfiguration
from openfga_sdk.client.models import (
    ClientCheckRequest,
    ClientWriteRequest,
    ClientTuple,
    ClientWriteResponse,
)
from openfga_sdk.models import CheckResponse, ListObjectsResponse
from app.config import settings

ROLES = ["admin", "member"]

# Set up logging
logger = logging.getLogger(__name__)


class AuthorizationService:
    """RBAC authorization service using OpenFGA."""

    def __init__(self):
        # Initialize OpenFgaClient with configuration
        configuration = ClientConfiguration(
            api_url=settings.openfga_api_url,
            store_id=settings.openfga_store_id,
            authorization_model_id=settings.openfga_authorization_model_id,
        )
        self.client = OpenFgaClient(configuration)

    # Core OpenFGA operations
    async def _check_permission(self, user: str, relation: str, object_id: str) -> CheckResponse:
        """Check if a user has a specific relation to an object."""
        return await self.client.check(
            ClientCheckRequest(user=user, relation=relation, object=object_id)
        )

    async def _write_tuples(self, tuples: list[ClientTuple]) -> ClientWriteResponse:
        """Write relationship tuples to OpenFGA."""
        logger.debug(f"Writing {len(tuples)} tuples to OpenFGA")
        write_request = ClientWriteRequest(writes=tuples)
        return await self.client.write(write_request)

    async def _delete_tuples(self, tuples: list[ClientTuple]) -> ClientWriteResponse:
        """Delete relationship tuples from OpenFGA."""
        logger.debug(f"Deleting {len(tuples)} tuples from OpenFGA")
        write_request = ClientWriteRequest(deletes=tuples)
        return await self.client.write(write_request)

    async def _list_objects(self, user: str, relation: str, object_type: str) -> ListObjectsResponse:
        """List all objects of a given type that a user has a specific relation to."""
        logger.debug(
            f"Listing objects: user={user}, relation={relation}, type={object_type}"
        )
        return await self.client.list_objects(
            user=user, relation=relation, type=object_type
        )

    # Business logic methods
    async def assign_user_to_organization(
        self, user_id: str, organization_id: str, role: str
    ) -> bool:
        """Assign a user to an organization with a specific role (admin or member)."""
        if role not in ROLES:
            raise ValueError(f"Role must be in: {ROLES}")

        client_tuple = ClientTuple(
            user=f"user:{user_id}",
            relation=role,
            object=f"organization:{organization_id}",
        )
        response = await self._write_tuples([client_tuple])
        return response is not None

    async def remove_user_from_organization(
        self, user_id: str, organization_id: str, role: str
    ) -> bool:
        """Remove a user's role from an organization."""
        if role not in ROLES:
            raise ValueError(f"Role must be in: {ROLES}")

        client_tuple = ClientTuple(
            user=f"user:{user_id}",
            relation=role,
            object=f"organization:{organization_id}",
        )
        response = await self._delete_tuples([client_tuple])
        return response is not None

    async def assign_resource_to_organization(
        self, resource_id: str, organization_id: str
    ) -> bool:
        """Assign a resource to an organization."""
        client_tuple = ClientTuple(
            user=f"organization:{organization_id}",
            relation="organization",
            object=f"resource:{resource_id}",
        )
        response = await self._write_tuples([client_tuple])
        return response is not None

    async def check_permission_on_resource(
        self, user_id: str, action: str, resource_id: str
    ) -> bool:
        """Check if user is allowed to perform an action on a resource."""
        response = await self._check_permission(
            user=f"user:{user_id}", relation=action, object_id=f"resource:{resource_id}"
        )
        return response.allowed if response else False

    async def check_permission_on_org(
        self, user_id: str, action: str, org_id: str
    ) -> bool:
        """Check if user is allowed to perform an action on an organization."""
        response = await self._check_permission(
            user=f"user:{user_id}", relation=action, object_id=f"organization:{org_id}"
        )
        return response.allowed if response else False

    async def get_user_organizations(self, user_id: str) -> List[str]:
        """Get all organizations a user is a member of."""
        admin_response = await self._list_objects(
            user=f"user:{user_id}", relation="admin", object_type="organization"
        )
        member_response = await self._list_objects(
            user=f"user:{user_id}", relation="member", object_type="organization"
        )

        admin_orgs = admin_response.objects if admin_response and hasattr(admin_response, "objects") else []
        member_orgs = member_response.objects if member_response and hasattr(member_response, "objects") else []

        # Remove duplicates and organization: prefix
        all_orgs = list(set(admin_orgs + member_orgs))
        return [org.replace("organization:", "") for org in all_orgs]

    async def get_user_resources(self, user_id: str) -> List[str]:
        """Get all resources a user can view."""
        response = await self._list_objects(
            user=f"user:{user_id}", relation="can_view_resource", object_type="resource"
        )
        resources = response.objects if response and hasattr(response, "objects") else []
        # Remove resource: prefix
        return [res.replace("resource:", "") for res in resources]

    async def check_fga_health(self) -> bool:
        """Check if OpenFGA service is healthy."""
        try:
            await self.client.read_authorization_models()
            return True
        except Exception as e:
            logger.error(f"OpenFGA health check failed: {e}")
            return False


# Global authorization service instance
authz_service = AuthorizationService()
