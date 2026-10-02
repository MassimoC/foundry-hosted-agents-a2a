# -----------------------------------------
# ------
# Agent card only v0.3:
# py .\04-foundry-a2a-test-raw-syncasync.py "here the text" --agent-name test-harness-research --card-only
#
# Agent card only v1.0:
# py .\04-foundry-a2a-test-raw-syncasync.py "here the text" --agent-name test-harness-research --agent-card-path agentCard/v1.0 --card-only
#
# Blocking:
# py .\04-foundry-a2a-test-raw-syncasync.py "cloud hybervisor vs hyperlight. do not ask user for additional approval, just execute your plan" --agent-name test-harness-research --agent-card-path agentCard/v1.0
#
# Non-blocking / async:
# py .\04-foundry-a2a-test-raw-syncasync.py "cloud hybervisor vs hyperlight. do not ask user for additional approval, just execute your plan" --agent-name test-harness-research --async
#
# Non-blocking with custom polling interval:
# py .\04-foundry-a2a-test-raw-syncasync.py "cloud hybervisor vs hyperlight. do not ask user for additional approval, just execute your plan" --agent-name test-harness-research --async --poll-seconds 2
#
# Non-blocking with custom timeout:
# py .\04-foundry-a2a-test-raw-syncasync.py "cloud hybervisor vs hyperlight" --agent-name test-harness-research --async --timeout-seconds 600
#
# ------
# -----------------------------------------

import argparse
import asyncio
import json
import os
import sys

import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.client.client import ClientCallContext
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import (
    GetTaskRequest,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    TaskState,
)
from azure.identity import DefaultAzureCredential
from google.protobuf.json_format import MessageToJson


# -------------------------------------------------------------------
# Trace context
#
# We keep the first trace returned by Foundry.
# This is useful in async mode because subsequent tasks/get calls
# may have their own request/span correlation identifiers.
# -------------------------------------------------------------------

trace_context = {
    "trace_id": None,
    "traceparent": None,
    "request_id": None,
    "client_request_id": None,
    "session_id": None,
    "foundry_call_id": None,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a text message to a Foundry-hosted A2A agent."
    )

    parser.add_argument(
        "text",
        help="Text message to send to the agent.",
    )

    parser.add_argument(
        "--endpoint",
        default=os.environ.get(
            "FOUNDRY_PROJECT_ENDPOINT",
            "https://mmcx-foundry.services.ai.azure.com/api/projects/mmcx-project",
        ),
    )

    parser.add_argument(
        "--agent-name",
        default=os.environ.get(
            "FOUNDRY_AGENT_NAME",
            "harness",
        ),
    )

    parser.add_argument(
        "--agent-card-path",
        default=os.environ.get(
            "A2A_AGENT_CARD_PATH",
            "agentCard/v0.3",
        ),
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(
            os.environ.get(
                "A2A_TIMEOUT_SECONDS",
                "240",
            )
        ),
        help="Timeout for each A2A HTTP request. Default: 240 seconds.",
    )

    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=float(
            os.environ.get(
                "A2A_POLL_SECONDS",
                "2",
            )
        ),
        help="Polling interval when using --async. Default: 2 seconds.",
    )

    parser.add_argument(
        "--async",
        "--non-blocking",
        dest="async_mode",
        action="store_true",
        help=(
            "Send the A2A request asynchronously "
            "and poll the returned task."
        ),
    )

    parser.add_argument(
        "--card-only",
        action="store_true",
    )

    return parser


# -------------------------------------------------------------------
# TRACE HELPERS
# -------------------------------------------------------------------

def extract_trace_id(traceparent: str | None) -> str | None:
    """
    Extract the trace ID from a W3C traceparent header.

    Format:

        version-trace_id-parent_id-flags

    Example:

        00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01

    Trace ID:

        4bf92f3577b34da6a3ce929d0e0e4736
    """

    if not traceparent:
        return None

    parts = traceparent.split("-")

    if len(parts) >= 4:
        return parts[1]

    return None


def capture_trace_headers(response: httpx.Response) -> dict:
    """
    Extract useful tracing/correlation headers from the response.
    """

    traceparent = response.headers.get("traceparent")
    trace_id = extract_trace_id(traceparent)

    request_id = response.headers.get("x-request-id")
    client_request_id = response.headers.get(
        "x-ms-client-request-id"
    )

    session_id = response.headers.get(
        "x-agent-session-id"
    )

    foundry_call_id = response.headers.get(
        "x-agent-foundry-call-id"
    )

    current_trace = {
        "trace_id": trace_id,
        "traceparent": traceparent,
        "request_id": request_id,
        "client_request_id": client_request_id,
        "session_id": session_id,
        "foundry_call_id": foundry_call_id,
    }

    # Keep the first available trace information.
    #
    # In async mode, tasks/get requests can generate additional
    # correlation information, while we normally care most about
    # the initial agent invocation.
    if trace_context["trace_id"] is None and trace_id:
        trace_context["trace_id"] = trace_id
        trace_context["traceparent"] = traceparent
        trace_context["request_id"] = request_id
        trace_context["client_request_id"] = client_request_id
        trace_context["session_id"] = session_id
        trace_context["foundry_call_id"] = foundry_call_id

    # If no traceparent exists but Foundry gave us an x-request-id,
    # keep that as correlation information as well.
    if (
        trace_context["request_id"] is None
        and request_id
    ):
        trace_context["request_id"] = request_id

    if (
        trace_context["client_request_id"] is None
        and client_request_id
    ):
        trace_context["client_request_id"] = client_request_id

    if (
        trace_context["session_id"] is None
        and session_id
    ):
        trace_context["session_id"] = session_id

    if (
        trace_context["foundry_call_id"] is None
        and foundry_call_id
    ):
        trace_context["foundry_call_id"] = foundry_call_id

    return current_trace


def print_trace_information(trace: dict) -> None:
    """
    Print tracing information only when Foundry returned it.
    """

    values_present = any(trace.values())

    if not values_present:
        return

    print("\nTracing:")

    if trace["traceparent"]:
        print(
            f"traceparent:             "
            f"{trace['traceparent']}"
        )

    if trace["trace_id"]:
        print(
            f"TRACE ID:                "
            f"{trace['trace_id']}"
        )

    if trace["request_id"]:
        print(
            f"x-request-id:            "
            f"{trace['request_id']}"
        )

    if trace["client_request_id"]:
        print(
            f"x-ms-client-request-id:  "
            f"{trace['client_request_id']}"
        )

    if trace["session_id"]:
        print(
            f"x-agent-session-id:      "
            f"{trace['session_id']}"
        )

    if trace["foundry_call_id"]:
        print(
            f"x-agent-foundry-call-id: "
            f"{trace['foundry_call_id']}"
        )


def print_final_trace_summary() -> None:
    """
    Print the trace/correlation information captured
    from the initial Foundry invocation.
    """

    if not any(trace_context.values()):
        return

    print("\n========== FOUNDRY TRACE ==========")

    if trace_context["trace_id"]:
        print(
            f"Trace ID:                "
            f"{trace_context['trace_id']}"
        )

    if trace_context["traceparent"]:
        print(
            f"Traceparent:             "
            f"{trace_context['traceparent']}"
        )

    if trace_context["request_id"]:
        print(
            f"Request ID:              "
            f"{trace_context['request_id']}"
        )

    if trace_context["client_request_id"]:
        print(
            f"Client Request ID:       "
            f"{trace_context['client_request_id']}"
        )

    if trace_context["session_id"]:
        print(
            f"Agent Session ID:        "
            f"{trace_context['session_id']}"
        )

    if trace_context["foundry_call_id"]:
        print(
            f"Foundry Call ID:         "
            f"{trace_context['foundry_call_id']}"
        )

    print("===================================\n")


# -------------------------------------------------------------------
# HTTP LOGGING
# -------------------------------------------------------------------

async def log_request(request: httpx.Request) -> None:
    print("\n========== OUTGOING HTTP REQUEST ==========")
    print(f"{request.method} {request.url}")

    print("\nHeaders:")

    for key, value in request.headers.items():
        if key.lower() == "authorization":
            print(
                f"{key}: Bearer ***REDACTED***"
            )
        else:
            print(
                f"{key}: {value}"
            )

    if request.content:
        print("\nBody:")

        try:
            body = json.loads(request.content)

            print(
                json.dumps(
                    body,
                    indent=2,
                )
            )

        except Exception:
            print(
                request.content.decode(
                    "utf-8",
                    errors="replace",
                )
            )

    print(
        "===========================================\n"
    )


async def log_response(response: httpx.Response) -> None:
    await response.aread()

    print(
        "\n========== INCOMING HTTP RESPONSE ========="
    )

    print(
        f"Status: {response.status_code}"
    )

    # ---------------------------------------------------------------
    # Trace/correlation headers
    # ---------------------------------------------------------------

    trace = capture_trace_headers(response)

    print_trace_information(trace)

    # ---------------------------------------------------------------
    # All response headers
    # ---------------------------------------------------------------

    print("\nHeaders:")

    for key, value in response.headers.items():
        print(
            f"{key}: {value}"
        )

    # ---------------------------------------------------------------
    # Body
    # ---------------------------------------------------------------

    print("\nBody:")

    try:
        body = json.loads(response.content)

        print(
            json.dumps(
                body,
                indent=2,
            )
        )

    except Exception:
        print(response.text)

    print(
        "===========================================\n"
    )


# -------------------------------------------------------------------
# TASK POLLING
# -------------------------------------------------------------------

async def poll_task(
    client,
    task_id: str,
    poll_seconds: float,
    timeout_seconds: float,
) -> int:

    terminal_states = {
        TaskState.TASK_STATE_COMPLETED,
        TaskState.TASK_STATE_FAILED,
        TaskState.TASK_STATE_CANCELED,
        TaskState.TASK_STATE_REJECTED,
    }

    # These require external action and will not progress simply
    # by continuing to poll.
    interrupted_states = {
        TaskState.TASK_STATE_INPUT_REQUIRED,
        TaskState.TASK_STATE_AUTH_REQUIRED,
    }

    print(
        f"\nTask created: {task_id}"
    )

    print(
        f"Polling every {poll_seconds} seconds...\n"
    )

    previous_state = None

    while True:

        task = await client.get_task(
            GetTaskRequest(
                id=task_id,
            ),
            context=ClientCallContext(
                timeout=timeout_seconds,
            ),
        )

        state = task.status.state
        state_name = TaskState.Name(state)

        if state != previous_state:

            print(
                f"[TASK UPDATE] "
                f"{task_id} -> {state_name}"
            )

            previous_state = state

        # -----------------------------------------------------------
        # TERMINAL
        # -----------------------------------------------------------

        if state in terminal_states:

            print(
                "\n========== FINAL TASK =========="
            )

            print(
                MessageToJson(
                    task,
                    preserving_proto_field_name=False,
                    indent=2,
                )
            )

            print(
                "================================\n"
            )

            print_final_trace_summary()

            if (
                state
                == TaskState.TASK_STATE_COMPLETED
            ):
                return 0

            return 1

        # -----------------------------------------------------------
        # INTERRUPTED
        # -----------------------------------------------------------

        if state in interrupted_states:

            print(
                "\n========== TASK INTERRUPTED =========="
            )

            print(
                MessageToJson(
                    task,
                    preserving_proto_field_name=False,
                    indent=2,
                )
            )

            print(
                "=====================================\n"
            )

            print_final_trace_summary()

            return 2

        await asyncio.sleep(
            poll_seconds
        )


# -------------------------------------------------------------------
# MAIN A2A FLOW
# -------------------------------------------------------------------

async def run(args: argparse.Namespace) -> int:

    a2a_base_url = (
        f"{args.endpoint.rstrip('/')}"
        f"/agents/{args.agent_name}"
        f"/endpoint/protocols/a2a"
    )

    credential = DefaultAzureCredential()

    token = credential.get_token(
        "https://ai.azure.com/.default"
    ).token

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=httpx.Timeout(
            args.timeout_seconds
        ),
        event_hooks={
            "request": [log_request],
            "response": [log_response],
        },
    ) as httpx_client:

        # -----------------------------------------------------------
        # Resolve agent card
        # -----------------------------------------------------------

        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=a2a_base_url,
            agent_card_path=args.agent_card_path,
        )

        agent_card = await resolver.get_agent_card()

        if args.card_only:

            print(
                MessageToJson(
                    agent_card
                )
            )

            return 0

        # -----------------------------------------------------------
        # Create A2A client
        # -----------------------------------------------------------

        config = ClientConfig(
            streaming=False,
            httpx_client=httpx_client,
        )

        client = await create_client(
            agent=agent_card,
            client_config=config,
        )

        try:

            message = new_text_message(
                args.text,
                role=Role.ROLE_USER,
            )

            # =======================================================
            # NON-BLOCKING / ASYNC
            # =======================================================

            if args.async_mode:

                request = SendMessageRequest(
                    message=message,
                    configuration=SendMessageConfiguration(
                        return_immediately=True,
                    ),
                )

                task_id = None

                call_context = ClientCallContext(
                    timeout=args.timeout_seconds
                )

                async for response in client.send_message(
                    request,
                    context=call_context,
                ):

                    print(
                        "\n========== INITIAL A2A RESPONSE =========="
                    )

                    print(
                        MessageToJson(
                            response,
                            preserving_proto_field_name=False,
                            indent=2,
                        )
                    )

                    print(
                        "==========================================\n"
                    )

                    if response.HasField("task"):
                        task_id = response.task.id

                if not task_id:
                    raise RuntimeError(
                        "The non-blocking A2A request "
                        "did not return a task ID."
                    )

                return await poll_task(
                    client=client,
                    task_id=task_id,
                    poll_seconds=args.poll_seconds,
                    timeout_seconds=args.timeout_seconds,
                )

            # =======================================================
            # BLOCKING
            # =======================================================

            request = SendMessageRequest(
                message=message
            )

            call_context = ClientCallContext(
                timeout=args.timeout_seconds
            )

            async for response in client.send_message(
                request,
                context=call_context,
            ):

                print(
                    "\n========== A2A RESPONSE =========="
                )

                print(
                    MessageToJson(
                        response,
                        preserving_proto_field_name=False,
                        indent=2,
                    )
                )

                print(
                    "==================================\n"
                )

            print_final_trace_summary()

            return 0

        finally:
            await client.close()


# -------------------------------------------------------------------
# ENTRYPOINT
# -------------------------------------------------------------------

def main() -> None:

    parser = build_parser()
    args = parser.parse_args()

    try:

        raise SystemExit(
            asyncio.run(
                run(args)
            )
        )

    except KeyboardInterrupt:
        raise SystemExit(130) from None

    except Exception as exc:  # noqa: BLE001

        print(
            f"ERROR: "
            f"{type(exc).__name__}: "
            f"{exc}",
            file=sys.stderr,
        )

        print_final_trace_summary()

        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()