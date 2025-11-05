from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routes import organization_routes, resource_routes
from app.services.authorization_service import authz_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.app_title} v{settings.app_version}")
    print(f"OpenFGA API URL: {settings.openfga_api_url}")
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully!")

    # Check OpenFGA connection
    print("Checking OpenFGA connection...")
    fga_healthy = await authz_service.check_fga_health()
    if fga_healthy:
        print("OpenFGA connection established successfully!")
    else:
        print("Warning: OpenFGA connection failed. Check your configuration.")

    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="FastAPI OpenFGA RBAC Demo",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    description="""
    A simple FastAPI application demonstrating RBAC (Role-Based Access Control) using OpenFGA.

    This demo showcases:
    - Organizations with admin/member roles
    - Resources owned by organizations
    - Permission inheritance from organization roles to resource permissions

    ## RBAC Model
    - **admin**: Can manage organization members and delete resources
    - **member**: Can view organization members and resources, create new resources
    - **Resources**: Inherit permissions from their owning organization

    All authorization is handled through OpenFGA using a simple, coarse-grained access control model.
    """,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    organization_routes.router, prefix="/organizations", tags=["organizations"]
)
app.include_router(resource_routes.router, prefix="/resources", tags=["resources"])


@app.get("/")
async def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to the FastAPI OpenFGA RBAC Demo!",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
        "model": "Simple RBAC with organizations and resources",
        "roles": ["admin", "member"],
        "example_usage": {
            "1": "Create an organization (user becomes admin)",
            "2": "Add members to the organization",
            "3": "Create resources in the organization",
            "4": "Check permissions on resources",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint including OpenFGA status."""
    fga_healthy = await authz_service.check_fga_health()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "openfga": "connected" if fga_healthy else "disconnected",
    }


@app.get("/rbac-info")
async def rbac_info():
    """Information about the RBAC model implementation."""
    return {
        "model": "OpenFGA RBAC Implementation",
        "pattern": "Coarse-grained access control",
        "types": {
            "user": "Individual users in the system",
            "organization": "Groups that contain users with roles",
            "resource": "Assets owned by organizations",
        },
        "roles": {
            "admin": {
                "description": "Full control over organization and its resources",
                "permissions": [
                    "can_add_member",
                    "can_delete_member",
                    "can_view_member",
                    "can_add_resource",
                    "can_delete_resource",
                    "can_view_resource",
                ],
            },
            "member": {
                "description": "Basic access to organization and resources",
                "permissions": [
                    "can_view_member",
                    "can_add_resource",
                    "can_view_resource",
                ],
            },
        },
        "inheritance": "Resource permissions inherit from organization roles via 'admin from organization' and 'member from organization' patterns",
    }
