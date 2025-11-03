# FastAPI OpenFGA RBAC Demo

This project demonstrates how to implement **Role-Based Access Control (RBAC)** using OpenFGA with FastAPI. It follows OpenFGA's best practices for coarse-grained access control, starting simple and building up complexity gradually.

## RBAC Model Overview

This demo implements a simple organizational RBAC pattern with:

- **Organizations**: Groups that contain users with specific roles
- **Users**: Individual actors with roles in organizations
- **Resources**: Assets owned by organizations
- **Roles**: `admin` and `member` with different permission levels

## OpenFGA Model

```yaml
type user

type organization
  relations
    define admin: [user]
    define member: [user]

    define can_add_member: admin
    define can_delete_member: admin
    define can_view_member: admin or member
    define can_add_resource: admin or member

type resource
  relations
    define organization: [organization]

    define can_delete_resource: admin from organization
    define can_view_resource: admin from organization or member from organization
```

## Key RBAC Concepts Demonstrated

### 1. **Direct Role Assignment**
- Users are directly assigned `admin` or `member` roles in organizations

### 2. **Permission Inheritance**
- Resource permissions inherit from organization roles
- Uses OpenFGA's `from` keyword to map organization roles to resource permissions
- `admin from organization` means "users who are admins of the organization that owns this resource"

### 3. **Persistent Data Storage**
- Uses SQLite database with SQLAlchemy for data persistence
- Data survives server restarts unlike in-memory storage
- ACID compliance ensures data integrity

## Permission Matrix

| Role | Add Members | Delete Members | View Members | Add Resources | Delete Resources | View Resources |
|------|-------------|----------------|--------------|---------------|------------------|----------------|
| **admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **member** | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |

## Project Structure

```
fastapi-openfga-project/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Configuration settings
│   ├── database.py              # SQLAlchemy database setup and models
│   ├── models/
│   │   ├── organization.py      # Organization Pydantic models
│   │   └── resource.py          # Resource Pydantic models
│   ├── routes/
│   │   ├── organization_routes.py # Organization management endpoints
│   │   └── resource_routes.py   # Resource management endpoints
│   ├── services/
│   │   └── authorization_service.py # OpenFGA integration
│   ├── utils/
│   │   └── openfga_client.py    # OpenFGA client wrapper
│   └── openfga/
│       └── model.fga.yaml       # OpenFGA model definition
├── app.db                       # SQLite database file (auto-created)
├── requirements.txt
└── README.md
```

## Features

- **Role-Based Access Control**: OpenFGA-powered authorization
- **Persistent Storage**: SQLite database with SQLAlchemy ORM
- **Async Support**: Full async/await support for database operations
- **Auto-reload**: Development server with hot reload
- **API Documentation**: Interactive Swagger UI documentation
- **Data Validation**: Pydantic models for request/response validation

## Requirements

- Python 3.9+

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   Don't forget to add your credentials!

3. **Run the Application**
   ```bash
   uvicorn app.main:app --reload
   ```

   The application will:
   - Connect to OpenFGA
   - Initialize SQLite database tables automatically
   - Start the FastAPI server on http://127.0.0.1:8000

5. **Access the API**
   - API Documentation: http://127.0.0.1:8000/docs
   - RBAC Info: http://127.0.0.1:8000/rbac-info
   - Health Check: http://127.0.0.1:8000/health

## Dependencies

- **FastAPI 0.115.0**: Modern web framework for building APIs
- **SQLAlchemy 2.0.36**: SQL toolkit and Object-Relational Mapping
- **aiosqlite 0.20.0**: Async SQLite driver
- **OpenFGA SDK 0.9.5**: [OpenFGA python client library](https://github.com/openfga/python-sdk)
- **Pydantic 2.10.0**: Data validation and settings management
- **Uvicorn 0.32.0**: ASGI server implementation

## API Endpoints

### Organizations
- `GET /organizations` - List accessible organizations
- `POST /organizations` - Create organization (creator becomes admin)
- `GET /organizations/{id}` - Get organization details
- `DELETE /organizations/{id}` - Delete organization (admin only)
- `POST /organizations/{id}/members` - Add member (admin only)
- `DELETE /organizations/{id}/members/{user_id}` - Remove member (admin only)

### Resources
- `GET /resources` - List accessible resources
- `POST /resources` - Create resource (admin or member)
- `GET /resources/{id}` - Get resource details
- `DELETE /resources/{id}` - Delete resource (admin only)
- `GET /resources/{id}/permissions` - Check user permissions on resource

## Example Usage Flow

1. **Create an Organization**
   ```bash
   curl -X POST "http://localhost:8000/organizations?user_id=alice" \
        -H "Content-Type: application/json" \
        -d '{"name": "Acme Corp", "description": "Example organization"}'
   ```

2. **Add a Member**
   ```bash
   curl -X POST "http://localhost:8000/organizations/{org_id}/members?user_id=alice" \
        -H "Content-Type: application/json" \
        -d '{"user_id": "bob", "role": "member", "organization_id": "{org_id}"}'
   ```

3. **Create a Resource**
   ```bash
   curl -X POST "http://localhost:8000/resources?user_id=bob" \
        -H "Content-Type: application/json" \
        -d '{"name": "Database Server", "resource_type": "database", "organization_id": "{org_id}"}'
   ```

4. **Check Permissions**
   ```bash
   curl "http://localhost:8000/resources/{resource_id}/permissions?user_id=bob"
   ```

## Next Steps for Extension

This basic RBAC model can be extended by:

1. Adding more roles (e.g., `viewer`, `manager`)
2. Implementing resource-specific permissions
3. Adding hierarchical organizations
4. Implementing time-based access controls
5. Adding attribute-based access control (ABAC) elements

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
