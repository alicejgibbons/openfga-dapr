# Dapr & OpenFGA: Employee Onboarding Workflow

This directory contains an example of using [Dapr Workflow](https://docs.dapr.io/developing-applications/building-blocks/workflow/) along with [OpenFGA](https://openfga.dev/) to create an employee onboarding workflow that simulates the process needed to onboard a user to an enterprise Auth server and give them the associated permissions.

## Prerequisites
- [OpenFGA CLI](https://github.com/openfga/cli?tab=readme-ov-file#installation)
- [Dapr CLI and initialized environment](https://docs.dapr.io/getting-started)
- [Install Python 3.9+](https://www.python.org/downloads/)

### Install requirements

You can install Dapr SDK package using pip command:

```sh
pip3 install -r requirements.txt
```

## Setup OpenFGA Server locally

1. See [Setup OpenFGA with Docker](https://openfga.dev/docs/getting-started/setup-openfga/docker).

```
make dev-setup

Starting OpenFGA...
80709f850f5fbbe0b00dd6d0a3b194d72049fbc58593e89182ee9e363a5f1d23
OpenFGA started on:
  - HTTP API: http://localhost:8080
  - gRPC API: localhost:8081
  - Playground: http://localhost:3000
Waiting for OpenFGA to be ready...
Importing OpenFGA store...

✓ Store imported successfully!
  Store ID: 01K9FTEV5JFSSDX6TQXRDN51N0
  Model ID: 01K9FTEV5N47EE7N16T7BMXVCJ
  Configuration saved to: .env


✓ Development environment ready!
  - OpenFGA: http://localhost:8080
  - Playground: http://localhost:3000/playground
```


2. Create org

```
curl --request POST --url 'http://localhost:8080/organizations/?user_id=alice' --header 'content-type: application/json' --data '{"name": "acme","description": "A demo organization"}'
```


## Run the User onboarding workflow

Each of the examples in this directory can be run directly from the command line.

This example demonstrates how to chain "activity" tasks together in a workflow. You can run this sample using the following command:

```sh
dapr run --app-id create_resource_workflow --dapr-grpc-port 50001 --dapr-http-port 3500 --resources-path ./resources -- python workflows.py
```

The output of this example should look like this:

```
== APP == Workflow started. Instance ID: b716208586c24829806b44b62816b598
== APP == Step 1: Received input: 42.
== APP == Step 2: Received input: 43.
== APP == Step 3: Received input: 86.
== APP == Workflow completed! Status: WorkflowStatus.COMPLETED
```
