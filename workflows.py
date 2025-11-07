# -*- coding: utf-8 -*-
# Copyright 2023 The Dapr Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid
from datetime import datetime

from app.database import ResourceDB

import time
import logging
from datetime import datetime, timedelta
from dapr.ext.workflow import (
    WorkflowRuntime,
    DaprWorkflowContext,
    WorkflowActivityContext,
    RetryPolicy,
    DaprWorkflowClient,
    when_any,
)

from app.config import settings
from app.services.authorization_service import authz_service
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Create sync engine
engine = create_engine(
    "sqlite:///./db.sqlite3",
    echo=False,
)

# Create sync session factory
Session = sessionmaker(engine, expire_on_commit=False)


wfr = WorkflowRuntime()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflows")

retry_policy = RetryPolicy(
    first_retry_interval=timedelta(seconds=1),
    max_number_of_attempts=3,
    backoff_coefficient=2,
    max_retry_interval=timedelta(seconds=10),
    retry_timeout=timedelta(seconds=100),
)


@wfr.workflow(name="create_resource_workflow")
def create_resource_workflow(ctx: DaprWorkflowContext, wf_input: dict):
    try:
        allowed = yield ctx.call_activity(
            check_permission_on_org,
            input={
                "user_id": wf_input.get("user_id"),
                "organization_id": wf_input.get("organization_id"),
            },
        )

        if not allowed:
            raise Exception(
                "User does not have permission to add resource to organization"
            )

        resource = yield ctx.call_activity(
            create_resource,
            input={
                "user_id": wf_input.get("user_id"),
                "organization_id": wf_input.get("organization_id"),
            },
        )

        logger.info(f"Resource created successfully: {resource}")

        assigned = yield ctx.call_activity(
            assign_resource_to_organization,
            input={
                "resource_id": resource.get("id"),
                "organization_id": wf_input.get("organization_id"),
            },
        )

        logger.info(f"Resource assigned to organization: {assigned}")
    except Exception as e:
        yield ctx.call_activity(error_handler, input=str(e))
        raise

    return resource


@wfr.activity(name="check_permission_on_org")
def check_permission_on_org(ctx: DaprWorkflowContext, input: dict):
    user_id = input.get("user_id")
    organization_id = input.get("organization_id")
    logger.info(
        f"check permission on org activity called: user_id={user_id}, organization_id={organization_id}"
    )

    return authz_service.check_permission_on_org(
        user_id, "can_add_resource", organization_id
    )


@wfr.activity(name="create_resource")
def create_resource(ctx: DaprWorkflowContext, input: dict):
    user_id = input.get("user_id")
    organization_id = input.get("organization_id")

    with Session() as session:
        resource_id = str(uuid.uuid4())

        logger.info(f"Creating resource with id: {resource_id}")

        # Create resource in database
        resource_db = ResourceDB(
            id=resource_id,
            name=f"Resource-{resource_id}",
            description="Created via workflow",
            resource_type="file",
            organization_id=organization_id,
            created_at=datetime.now(),
        )

        session.add(resource_db)
        session.commit()
        session.refresh(resource_db)

        # Return the created resource
        return {
            "id": resource_db.id,
            "name": resource_db.name,
            "description": resource_db.description,
            "resource_type": resource_db.resource_type,
            "organization_id": resource_db.organization_id,
        }


@wfr.activity(name="assign_resource_to_organization")
def assign_resource_to_organization(ctx: DaprWorkflowContext, input: dict):
    resource_id = input.get("resource_id")
    organization_id = input.get("organization_id")

    return authz_service.assign_resource_to_organization(resource_id, organization_id)


@wfr.activity
def error_handler(ctx, error):
    logger.info(f"Executing error handler: {error}.")
    # Rollback permissions in the openfga server


def main():
    wfr.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        wfr.shutdown()


if __name__ == "__main__":
    main()
