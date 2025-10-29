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
from time import sleep

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

#from workflow import wfr, order_processing_workflow
#from model import InventoryItem, OrderPayload

wfr = WorkflowRuntime()

retry_policy = RetryPolicy(
    first_retry_interval=timedelta(seconds=1),
    max_number_of_attempts=3,
    backoff_coefficient=2,
    max_retry_interval=timedelta(seconds=10),
    retry_timeout=timedelta(seconds=100),
)

@wfr.workflow(name='user_onboarding_workflow')
def task_chain_workflow(ctx: DaprWorkflowContext, wf_input: int):
    try:
        result1 = yield ctx.call_activity(step1, input=wf_input)
        result2 = yield ctx.call_activity(step2, input=result1)
        result3 = yield ctx.call_activity(step3, input=result2)
    except Exception as e:
        yield ctx.call_activity(error_handler, input=str(e))
        raise
    # TODO update to set custom status
    return [result1, result2, result3]


@wfr.activity(name='step1')
def step1(ctx, activity_input):
    print(f'Step 1: Received input: {activity_input}.')
    # Do some work
    return activity_input + 1


@wfr.activity
def step2(ctx, activity_input):
    print(f'Step 2: Received input: {activity_input}.')
    # Do some work
    return activity_input * 2


@wfr.activity
def step3(ctx, activity_input):
    print(f'Step 3: Received input: {activity_input}.')
    # Do some work
    return activity_input ^ 2


@wfr.activity
def error_handler(ctx, error):
    print(f'Executing error handler: {error}.')
    # Do some compensating work


if __name__ == '__main__':
    wfr.start()
    sleep(10)  # wait for workflow runtime to start

    wf_client = DaprWorkflowClient()
    instance_id = wf_client.schedule_new_workflow(workflow=task_chain_workflow, input=43)
    print(f'Workflow started. Instance ID: {instance_id}')
    state = wf_client.wait_for_workflow_completion(instance_id)
    print(f'Workflow completed! Status: {state.runtime_status}')

    wfr.shutdown()
