#!/usr/bin/env python3
"""
Example script showing how to use the resource creation function.
"""

import asyncio
from app.services.resource import create_resource
from app.database import init_db


async def main():
    """Example of creating resources programmatically."""

    # Initialize database tables if they don't exist
    await init_db()
    print("📊 Database initialized")

    # Example 1: Create an API resource
    try:
        api_resource = await create_resource(
            name="User Management API",
            resource_type="api",
            organization_id="org-123",
            description="API for managing user accounts and profiles"
        )
        print(f"✅ Created API resource: {api_resource.id}")
    except Exception as e:
        print(f"❌ Failed to create API resource: {e}")


if __name__ == "__main__":
    asyncio.run(main())
