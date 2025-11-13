# Dapr & OpenFGA: Grant Organization Membership Workflow

This repository contains an example of using [Dapr Workflow](https://docs.dapr.io/developing-applications/building-blocks/workflow/) along with [OpenFGA](https://openfga.dev/) to create a workflow that simulates the process needed to add a user to a team with the neccessary permissions with durability and resilliency built-in. This application also showcases a workaround to the common dual-write database problem by wrapping the write to two databases with Dapr's workflow engine for durable execution.

## Prerequisites
- [OpenFGA CLI](https://github.com/openfga/cli?tab=readme-ov-file#installation)
- [Dapr CLI and initialized local environment](https://docs.dapr.io/getting-started)
- [Install Python 3.9+](https://www.python.org/downloads/)
- Note: This repo assumes a Unix/Linux machine.

## Setup OpenFGA Server locally

1. Start Open FGA locally using Docker and PostgreSQL as the database backend. See [Setup OpenFGA with Docker for more details](https://openfga.dev/docs/getting-started/setup-openfga/docker).

```
make dev-setup

Starting OpenFGA...
docker compose up -d
[+] Running 3/3
 ✔ Container postgres  Healthy                                                                                                                                  5.9s 
 ✔ Container migrate   Exited                                                                                                                                   6.4s 
 ✔ Container openfga   Started                                                                                                                                  6.4s 
OpenFGA started on:
  - HTTP API: http://localhost:8080
  - gRPC API: localhost:8081
  - Playground: http://localhost:3000
Waiting for OpenFGA to be ready...
Importing OpenFGA store...

✓ Store imported successfully!
  Store ID: 01K9PTWXBXTCCJ3GFSGC2QDABF
  Model ID: 01K9PTWXC6PN38VPSDCC639EV6
  Configuration saved to: .env


✓ Development environment ready!
  - OpenFGA: http://localhost:8080
  - Playground: http://localhost:3000/playground
```

### Install requirements

Install Dapr SDK package using pip command:

```sh
pip3 install -r requirements.txt
```

## Run the Grant Organization Membership workflow

1. Run the workflow and Dapr process using the following command:

```sh
dapr run --app-id grant-organization-membership-workflow \
  --dapr-grpc-port 50001 \
  --dapr-http-port 3500 \
  --resources-path ./resources \
  -- python workflows.py
```

This command:
- starts the Dapr sidecar process using the `app-id` "grant-organization-membership-workflow"
- Starts the Dapr workflow application using the [Redis component](resources/statestore.yaml) as the backing workflow statestore

Along with the Dapr process logs, you will see the application logs output the following:

```
== APP == 2025-11-13 10:39:06.772 WorkflowRuntime INFO: Registering workflow 'grant_organization_membership_workflow' with runtime
== APP == INFO:WorkflowRuntime:Registering workflow 'grant_organization_membership_workflow' with runtime
== APP == 2025-11-13 10:39:06.772 WorkflowRuntime INFO: Registering activity 'check_permission_on_org' with runtime
== APP == INFO:WorkflowRuntime:Registering activity 'check_permission_on_org' with runtime
== APP == 2025-11-13 10:39:06.772 WorkflowRuntime INFO: Registering activity 'approver_manual_override' with runtime
== APP == INFO:WorkflowRuntime:Registering activity 'approver_manual_override' with runtime
== APP == 2025-11-13 10:39:06.773 WorkflowRuntime INFO: Registering activity 'create_team_member' with runtime
== APP == INFO:WorkflowRuntime:Registering activity 'create_team_member' with runtime
== APP == 2025-11-13 10:39:06.773 WorkflowRuntime INFO: Registering activity 'assign_user_to_organization' with runtime
== APP == INFO:WorkflowRuntime:Registering activity 'assign_user_to_organization' with runtime
== APP == 2025-11-13 10:39:06.773 WorkflowRuntime INFO: Registering activity 'error_handler' with runtime
== APP == INFO:WorkflowRuntime:Registering activity 'error_handler' with runtime
== APP == 2025-11-13 10:39:06.773 durabletask-worker INFO: Starting gRPC worker that connects to dns:127.0.0.1:50001
== APP == 2025-11-13 10:39:06.777 durabletask-worker INFO: Created fresh connection to dns:127.0.0.1:50001
== APP == 2025-11-13 10:39:06.777 durabletask-worker INFO: Successfully connected to dns:127.0.0.1:50001. Waiting for work items...
```

## Kick off a new workflow

1. Use the VSCode Rest extension (or curl) and the [test.rest file](test.rest) file to start a new instance of the grant organization membership workflow.

```
POST {{daprHost}}/v1.0/workflows/dapr/grant_organization_membership_workflow/start
Content-Type: application/json

{
  "actor_id": "alice",
  "user_id": "charlie",
  "role": "member",
  "organization_id": "kubecon"
}
```

2. View the sqlite local database and confirm that Alice is, in fact, an admin in the `kubecon` org. A similar workflow run with Bob as the `actor_id` will fail with insufficient permissions.

| id | organization_id	| role |
|---|--------|-----|
| alice	| kubecon |	admin |
| bob	| kubecon	| member |

3. This workflow should complete successfully by adding Charlie to the sqlite and PostgreSQL OpenFGA authorization database. Use the `OpenFGA: ListUsers` and `Dapr Workflow: Get the workflow status` queries to confirm that the databases have been updated successfully. 

