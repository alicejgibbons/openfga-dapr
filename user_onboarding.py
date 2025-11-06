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

from datetime import datetime, timedelta
import os
import logging
import uvicorn

from dapr.clients import DaprClient
from dapr.conf import settings
from dapr.ext.workflow import (
    WorkflowRuntime,
    DaprWorkflowContext,
    WorkflowActivityContext,
    RetryPolicy,
    DaprWorkflowClient,
    when_any,
)

wfr = WorkflowRuntime()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('Workflows')

async def app(scope, receive, send):
    assert scope["type"] == "http"
    # Simple health response for any request
    body = b"healthy"
    headers = [(b"content-type", b"text/plain"), (b"content-length", str(len(body)).encode())]
    await send({"type": "http.response.start", "status": 200, "headers": headers})
    await send({"type": "http.response.body", "body": body})

retry_policy = RetryPolicy(
    first_retry_interval=timedelta(seconds=1),
    max_number_of_attempts=3,
    backoff_coefficient=2,
    max_retry_interval=timedelta(seconds=10),
    retry_timeout=timedelta(seconds=100),
)

@wfr.workflow(name='user_onboarding_workflow')
def user_onboarding_workflow(ctx: DaprWorkflowContext, wf_input: int):
    logger.info(f'User onboarding workflow started with workflow id: {ctx.instance_id} and input {wf_input}')
    try:
        result1 = yield ctx.call_activity(get_user_permissions, input=wf_input)
        logger.info(f'Result 1: {result1}')
        ctx.set_custom_status("User permissions retrieved")

        # For admin users wait for manual approval of permissions grant
        result2 = None
        if result1 == "admin":
            logger.info(f'inside admin')
            yield ctx.call_activity(notify_approver, input=wf_input)
            approved_event = ctx.wait_for_external_event('permissions_approved')
            denied_event = ctx.wait_for_external_event('permissions_denied')
            timeout_event = ctx.create_timer(timedelta(hours=24))
            winner = yield when_any([approved_event, timeout_event, denied_event])
            if winner == approved_event:
                result2 = 'Approved'
                ctx.set_custom_status("Admin permissions approved")
            else: 
                result2 = 'Denied'
                ctx.set_custom_status("Admin permissions denied or timed out")
                return [result2]
            logger.info(f'Admin permissions have been: {result2} for user id:{wf_input}')
        
        logger.info(f'Granting permissions for user id {wf_input}')
        result3 = yield ctx.call_activity(grant_permissions, input={'role': result1, 'user_id': wf_input})
        logger.info(f'after result3')
        
    except Exception as e:
        yield ctx.call_activity(error_handler, input=str(e))
        raise
    return [result2]


@wfr.activity(name='get_user_permissions')
def get_user_permissions(ctx, activity_input):
    logger.info(f'Getting user permissions for workflow id: {activity_input}')
    # Go get the state from the state store, for user id
    dapr_client = DaprClient()
    user_permissions = ""
    try:
        user_permissions = dapr_client.get_state(store_name='statestore', key=f'{activity_input}')
        if user_permissions.data:
            data = user_permissions.data.decode('utf-8') if isinstance(user_permissions.data, bytes) else user_permissions.data
            # Strip surrounding quotes if present (e.g., '"admin"' -> 'admin')
            if isinstance(data, str):
                data = data.strip().strip('"').strip("'")
        else:
            data = None
        return data
    except Exception as e:
        logger.info(f'Error getting user permissions: {e}')
        return None

@wfr.activity(name='notify_approver')
def notify_approver(ctx, activity_input):
    logger.info(f'Notifying approver to approve admin permissions. User id: {activity_input}')
    # TODO maybe have a ui here to approve?

@wfr.activity(name='grant_permissions')
def grant_permissions(ctx, activity_input):
    role = activity_input['role']
    user_id = activity_input['user_id']
    logger.info(f'Granting {role} permissions for user id {user_id}')
    # Grant permissions in the openfga server
    # PUT OPEN FGA SERVICE CALL HERE
    return f'Permissions granted for user {user_id} with role {role}'


@wfr.activity
def error_handler(ctx, error):
    logger.info(f'Executing error handler: {error}.')
    # Rollback permissions in the openfga server

def main():
    wfr.start()
    app_port = int(os.getenv('APP_PORT', 6005))
    logger.info(f"Starting FastAPI server on port {app_port}")
    uvicorn.run(app, host='0.0.0.0', port=app_port, log_level='info')

if __name__ == '__main__':
    main()

