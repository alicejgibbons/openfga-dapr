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
from dataclasses import dataclass

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
from demo.database import Resource
from demo.services.authorization_service import authz_service
from demo.database import Session


wfr = WorkflowRuntime()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflows")

@dataclass
class ResourceRequest:
    """Resource request object containing openfga request properties"""
    user_id: str
    name: str
    resource_type: str
    organization_id: str
    granted: bool = False
    resource_id: str = ""

retry_policy = RetryPolicy(
    first_retry_interval=timedelta(seconds=1),
    max_number_of_attempts=3,
    backoff_coefficient=2,
    max_retry_interval=timedelta(seconds=10),
    retry_timeout=timedelta(seconds=100),
)


@wfr.workflow(name="create_resource_workflow")
def create_resource_workflow(ctx: DaprWorkflowContext, wf_input: dict):
    req = ResourceRequest(
        user_id=wf_input.get("user_id"),
        name=wf_input.get("name"),
        resource_type=wf_input.get("resource_type"),
        organization_id=wf_input.get("organization_id"),
    )
    
    logger.info(f'Starting create resource workflow for access request for user: {req.user_id} on resource: {req.name}')
    try:
        allowed = yield ctx.call_activity(
            check_permission_on_org,
            input={
                "user_id": req.user_id,
                "organization_id": req.organization_id,
            },
        )

        if not allowed:  # in this case we should have a manual permission check
            ctx.set_custom_status("Insufficient user permissions on organization")
            logger.info(f'perms not allowed')
            yield ctx.call_activity(approver_manual_override, input=req.user_id)
            approved_event = ctx.wait_for_external_event('manual_override_approved')
            timeout_event = ctx.create_timer(timedelta(hours=24))
            winner = yield when_any([approved_event, timeout_event])
            if winner == approved_event:
                allowed = True
                logger.info(f'Admin permissions have been: {result2} for user id:{wf_input}')
                ctx.set_custom_status("Manual override - approved user permissions on organization")
            else: 
                raise Exception("User has insufficient permissions to add resource in organization")

        logger.info(f'User permission check passed: {allowed}')
        ctx.set_custom_status("User permissions confirmed")

        resource = yield ctx.call_activity(
            create_resource,
            input={
                "user_id": req.user_id,
                "organization_id": req.organization_id,
            },
        )

        logger.info(f"Resource created successfully: {resource}")
        ctx.set_custom_status(f"Resource {resource} created successfully")
        req.resource_id = resource.get("id")
        ## ideally workflow would fail here to showcase dual write problem

        assigned = yield ctx.call_activity(
            assign_resource_to_organization,
            input={
                "resource_id": req.resource_id,
                "organization_id": req.organization_id,
            },
        )

        logger.info(f"Resource assigned to organization: {assigned}")
        ctx.set_custom_status(f"Resource assigned to organization: {assigned}")
        req.granted = assigned
    except Exception as e:
        if req.resource_id != "":
            # TODO: Add compensating logic here
            yield ctx.call_activity(error_handler, input=str(e))
        return req.granted

    return req.granted


@wfr.activity(name="check_permission_on_org")
def check_permission_on_org(ctx: DaprWorkflowContext, input: dict):
    user_id = input.get("user_id")
    organization_id = input.get("organization_id")
    logger.info(f"Checked permission on org for user_id={user_id}, organization_id={organization_id}")

    return authz_service.check_permission_on_org(
        user_id, "can_add_resource", organization_id
    )

@wfr.activity(name='approver_manual_override')
def approver_manual_override(ctx, input):
    logger.info(f'Notifying approver to manual override permissions denial. User id: {input}')
    # TODO maybe have a ui here to approve?

@wfr.activity(name="create_resource")
def create_resource(ctx: DaprWorkflowContext, input: dict):
    resource_id = str(uuid.uuid4())

    user_id = input.get("user_id")
    name = input.get("name", f"resource-{str(uuid.uuid4())}")
    resource_type = input.get("resource_type", "file")
    organization_id = input.get("organization_id")

    with Session() as session:
        logger.info(f"Creating resource with id: {resource_id}")

        # Create resource in database
        resource_db = Resource(
            id=resource_id,
            name=name,
            resource_type=resource_type,
            organization_id=organization_id,
        )

        session.add(resource_db)
        session.commit()
        session.refresh(resource_db)

        # Return the created resource
        return {
            "id": resource_db.id
            # "name": resource_db.name,
            # "resource_type": resource_db.resource_type,
            # "organization_id": resource_db.organization_id,
        }


@wfr.activity(name="assign_resource_to_organization")
def assign_resource_to_organization(ctx: DaprWorkflowContext, input: dict):
    resource_id = input.get("resource_id")
    organization_id = input.get("organization_id")

    return authz_service.assign_resource_to_organization(resource_id, organization_id)


@wfr.activity
def error_handler(ctx, error):
    logger.info(f"Executing error handler: {error}.")
    # TODO: Add compensating logic here
