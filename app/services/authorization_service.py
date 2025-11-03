from typing import List
from openfga_sdk.client.models import ClientTuple
from app.utils.openfga_client import fga_client

ROLES = ["admin", "member"]


class AuthorizationService:
    """RBAC authorization service using OpenFGA."""

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
        return await fga_client.write_tuples([client_tuple])

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
        return await fga_client.delete_tuples([client_tuple])

    async def assign_resource_to_organization(
        self, resource_id: str, organization_id: str
    ) -> bool:
        """Assign a resource to an organization."""
        client_tuple = ClientTuple(
            user=f"organization:{organization_id}",
            relation="organization",
            object=f"resource:{resource_id}",
        )
        return await fga_client.write_tuples([client_tuple])

    async def check_permission_on_resource(
        self, user_id: str, action: str, resource_id: str
    ) -> bool:
        """Check if user is allowed to perform an action on a resource."""
        return await fga_client.check_permission(
            user=f"user:{user_id}", relation=action, object_id=f"resource:{resource_id}"
        )

    async def check_permission_on_org(
        self, user_id: str, action: str, org_id: str
    ) -> bool:
        """Check if user is allowed to perform an action on an organization."""
        return await fga_client.check_permission(
            user=f"user:{user_id}", relation=action, object_id=f"organization:{org_id}"
        )

    async def get_user_organizations(self, user_id: str) -> List[str]:
        """Get all organizations a user is a member of."""
        admin_orgs = await fga_client.list_objects(
            user=f"user:{user_id}", relation="admin", object_type="organization"
        )
        member_orgs = await fga_client.list_objects(
            user=f"user:{user_id}", relation="member", object_type="organization"
        )
        # Remove duplicates and organization: prefix
        all_orgs = list(set(admin_orgs + member_orgs))
        return [org.replace("organization:", "") for org in all_orgs]

    async def get_user_resources(self, user_id: str) -> List[str]:
        """Get all resources a user can view."""
        resources = await fga_client.list_objects(
            user=f"user:{user_id}", relation="can_view_resource", object_type="resource"
        )
        # Remove resource: prefix
        return [res.replace("resource:", "") for res in resources]

    async def check_fga_health(self) -> bool:
        """Check if OpenFGA service is healthy."""
        return await fga_client.health_check()


# Global authorization service instance
authz_service = AuthorizationService()
