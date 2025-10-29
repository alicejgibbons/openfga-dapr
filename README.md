# Dapr & OpenFGA: Employee Onboarding Workflow

This directory contains an example of using [Dapr Workflow](https://docs.dapr.io/developing-applications/building-blocks/workflow/) along with [OpenFGA](https://openfga.dev/) to create an employee onboarding workflow that simulates the process needed to onboard a user to an enterprise Auth server and give them the associated permissions. 

## Prerequisites

- [Dapr CLI and initialized environment](https://docs.dapr.io/getting-started)
- [Install Python 3.9+](https://www.python.org/downloads/)

### Install requirements

You can install Dapr SDK package using pip command:

```sh
pip3 install -r requirements.txt
```

## Setup OpenFGA Server locally

See [Setup OpenFGA with Docker](https://openfga.dev/docs/getting-started/setup-openfga/docker).

## Run the User onboarding workflow

Each of the examples in this directory can be run directly from the command line.

This example demonstrates how to chain "activity" tasks together in a workflow. You can run this sample using the following command:

```sh
dapr run --app-id user_onboarding_workflow --dapr-grpc-port 50001 --dapr-http-port 57742 --resources-path ./resources -- python3 user_onboarding.py
```

The output of this example should look like this:

```
== APP == Workflow started. Instance ID: b716208586c24829806b44b62816b598
== APP == Step 1: Received input: 42.
== APP == Step 2: Received input: 43.
== APP == Step 3: Received input: 86.
== APP == Workflow completed! Status: WorkflowStatus.COMPLETED
```
