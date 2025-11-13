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

from dataclasses import dataclass

import logging
from time import sleep
from datetime import timedelta
from dapr.ext.workflow import (
    WorkflowRuntime,
    DaprWorkflowContext,
    RetryPolicy,
    when_any,
)
from demo.database import TeamMember
from demo.services.authorization_service import authz_service
from demo.database import Session


wfr = WorkflowRuntime()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflows")


@dataclass
class TeamMemberRequest:
    """Team member request object containing openfga request properties"""
    actor_id: str
    user_id: str
    organization_id: str
    role: str
    created: bool = False
    granted: bool = False

retry_policy = RetryPolicy(
    first_retry_interval=timedelta(seconds=1),
    max_number_of_attempts=10,
    backoff_coefficient=1,
    max_retry_interval=timedelta(seconds=4),
    retry_timeout=timedelta(seconds=100),
)


@wfr.workflow(name="grant_organization_membership_workflow")
def grant_organization_membership_workflow(ctx: DaprWorkflowContext, wf_input: dict):
    req = TeamMemberRequest(
        actor_id=wf_input.get("actor_id"),
        user_id=wf_input.get("user_id"),
        role=wf_input.get("role"),
        organization_id=wf_input.get("organization_id"),
    )

    logger.info(
        f"Grant organization membership workflow for team member: {req.user_id} from user: {req.actor_id}"
    )
    try:
        allowed = yield ctx.call_activity(
            check_permission_on_org,
            input={
                "user_id": req.actor_id,
                "organization_id": req.organization_id,
                "relation": "can_add_member",
            },
            retry_policy=retry_policy,
        )

        if not allowed:
            ctx.set_custom_status("Insufficient requester user permissions to add team member in organization")
            yield ctx.call_activity(approver_manual_override, input=req.user_id)
            approved_event = ctx.wait_for_external_event("manual_override_approved")
            timeout_event = ctx.create_timer(timedelta(seconds=20))
            winner = yield when_any([approved_event, timeout_event])
            if winner == approved_event:
                allowed = True
                logger.info(
                    f"Manual override: approved adding team member to organization with user id:{req.user_id}"
                )
                ctx.set_custom_status(
                    "Manual override: approved adding team member to organization"
                )
            else:
                raise Exception(
                    "Requesting user has insufficient permissions to add team member in organization"
                )

        ctx.set_custom_status("Requster user permission check passed")

        team_member = yield ctx.call_activity(
            create_team_member,
            input={
                "user_id": req.user_id,
                "organization_id": req.organization_id,
                "role": req.role,
            },
        )
        req.created = True
        ctx.set_custom_status(f"Team member {team_member} created successfully")
        ## ideally workflow would fail here to showcase dual write problem

        if True:
            sleep(5)

        assigned = yield ctx.call_activity(
            assign_user_to_organization,
            input={
                "user_id": req.user_id,
                "organization_id": req.organization_id,
                "role": req.role,
            },
            retry_policy=retry_policy,
        )

        ctx.set_custom_status(f"Team member assigned to organization: {assigned}")
        req.granted = assigned

    except Exception as e:
        logger.error(
            f"Error in grant organization membership workflow for user_id={req.user_id}, organization_id={req.organization_id}: {e}"
        )
        ctx.set_custom_status(f"Error occurred: {e}")
        yield ctx.call_activity(
            error_handler,
            input={
                "user_id": req.user_id,
                "organization_id": req.organization_id,
                "role": req.role,
                "created": req.created,
                "granted": req.granted,
                "error": str(e),
            },
        )
        return req.granted

    return req.granted

@wfr.activity(name="check_permission_on_org")
def check_permission_on_org(ctx: DaprWorkflowContext, input: dict):
    user_id = input.get("user_id")
    organization_id = input.get("organization_id")
    relation = input.get("relation")
    logger.info(
        f"Checking permission on org for user_id={user_id}, organization_id={organization_id}"
    )
    allowed = authz_service.check_permission_on_org(user_id, relation, organization_id)
    logger.info(f"Requster user permission check passed: {allowed}")
    return allowed


@wfr.activity(name="approver_manual_override")
def approver_manual_override(ctx, input):
    logger.info(
        f"Notifying manual approver to override adding user to organization with user id: {input}"
    )

@wfr.activity(name="create_team_member")
def create_team_member(ctx: DaprWorkflowContext, input: dict):
    user_id = input.get("user_id")
    organization_id = input.get("organization_id")
    role = input.get("role")

    with Session() as session:
        logger.info(f"Creating team member for org: {user_id}")

        # Create team member in local database
        team_member = TeamMember(
            id=user_id,
            organization_id=organization_id,
            role=role,
        )

        session.merge(team_member)
        session.commit()
        logger.info(f"Team member created successfully: {team_member}")

        # Return the created team member
        return {"id": team_member.id}


@wfr.activity(name="assign_user_to_organization")
def assign_user_to_organization(ctx: DaprWorkflowContext, input: dict):
    user_id = input.get("user_id")
    organization_id = input.get("organization_id")
    role = input.get("role")

    assigned = authz_service.assign_user_to_organization(user_id, organization_id, role)
    logger.info(f"Team member assigned to organization: {assigned}")
    return assigned

@wfr.activity(name="error_handler")
def error_handler(ctx: DaprWorkflowContext, input: dict):
    error = input.get("error")
    user_id = input.get("user_id")
    organization_id = input.get("organization_id")
    role = input.get("role")
    created = input.get("created")
    granted = input.get("granted")
    logger.info(f"Executing error handler: {error}.")

    if granted:
        logger.info(
            f"Revoking OpenFGA permissions for user_id={user_id}, organization_id={organization_id}"
        )

        authz_service.remove_user_from_organization(user_id, organization_id, role)

    if created:
        logger.info(
            f"Deleting team member from database for user_id={user_id}, organization_id={organization_id}"
        )

        with Session() as session:
            session.query(TeamMember).filter(TeamMember.id == user_id).delete()
