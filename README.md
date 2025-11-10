# Dapr & OpenFGA: Grant Organization Membership Workflow

This repository contains an example of using [Dapr Workflow](https://docs.dapr.io/developing-applications/building-blocks/workflow/) along with [OpenFGA](https://openfga.dev/) to create a workflow that simulates the process needed to add a user to a team with the neccessary permissions with durability and resilliency built-in. This application also showcases a workaround to the common dual-write database problem by wrapping the write to two databases with Dapr's workflow engine for durable execution.

## Prerequisites
- [OpenFGA CLI](https://github.com/openfga/cli?tab=readme-ov-file#installation)
- [Dapr CLI and initialized environment](https://docs.dapr.io/getting-started)
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

2. Import the OpenFGA schema into the PostgreSQL database.

```
import-openfga-store

Importing OpenFGA store...

✓ Store imported successfully!
  Store ID: 01K9PVFK2DBQMCBCXYZHWTEM5B
  Model ID: 01K9PVFK2Q46H0P7H805V6A5NG
  Configuration saved to: .env
```

### Install requirements

Install Dapr SDK package using pip command:

```sh
pip3 install -r requirements.txt
```

## Run the Grant Organization Membership workflow

Each of the examples in this directory can be run directly from the command line.

This example demonstrates how to chain "activity" tasks together in a workflow. You can run this sample using the following command:

```sh
dapr run --app-id grant-organization-membership-workflow \
  --dapr-grpc-port 50001 \
  --dapr-http-port 3500 \
  --resources-path ./resources \
  -- python workflows.py
```

This command:
- starts the Dapr sidecar process using the `app-id` "organization-onboarding-workflow"
- Starts the Dapr workflow application

```
== APP == Workflow started. Instance ID: b716208586c24829806b44b62816b598
== APP == Step 1: Received input: 42.
== APP == Step 2: Received input: 43.
== APP == Step 3: Received input: 86.
== APP == Workflow completed! Status: WorkflowStatus.COMPLETED
```
