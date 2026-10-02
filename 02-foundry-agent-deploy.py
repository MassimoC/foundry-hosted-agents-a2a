# -----------------------------------------
# Usage:
#
# py .\02-foundry-agent-deploy.py `
#   --agent-name test-harness-research `
#   --project-endpoint https://mmcx-foundry.services.ai.azure.com/api/projects/mmcx-project `
#   --deployment-name gpt-5.6-luna `
#   --image-uri mmcxacr.azurecr.io/harness-research:91 `
#   --description "A research harness agent with web search, planning, todos, and compaction."
#
# Examples:
#
# py .\02-foundry-agent-deploy.py --agent-name harness-research --image-uri mmcxacr.azurecr.io/harness-research:91
# -----------------------------------------

import argparse
import os
import sys

import utils

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    HostedAgentDefinition,
    ProtocolVersionRecord,
    AgentEndpointProtocol,
    ContainerConfiguration,
)
from azure.identity import AzureCliCredential


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deploy a Foundry hosted agent."
    )

    parser.add_argument(
        "--agent-name",
        required=True,
        help="Name of the Foundry hosted agent.",
    )

    parser.add_argument(
        "--project-endpoint",
        required=False,
        default=os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "https://mmcx-foundry.services.ai.azure.com/api/projects/mmcx-project"),
        help="Foundry project endpoint.",
    )

    parser.add_argument(
        "--deployment-name",
        required=False,
        default=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5.6-luna"),
        help="Model deployment name.",
    )

    parser.add_argument(
        "--image-uri",
        required=True,
        default=os.environ.get("ACR_IMAGE_URI", "mmcxacr.azurecr.io/harness-research:101"),
        help="Container image URI.",
    )
    
    parser.add_argument(
        "--description",
        required=False,
        default="",
        help="Description of the Foundry hosted agent.",
    )

    return parser


def main():
    args = build_parser().parse_args()

    credential = AzureCliCredential()

    project = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=credential,
        allow_preview=True,
    )

    agent = project.agents.create_version(
        agent_name=args.agent_name,
        description=args.description,
        definition=HostedAgentDefinition(
            protocol_versions=[
                ProtocolVersionRecord(
                    protocol=AgentEndpointProtocol.RESPONSES,
                    version="2.0.0",
                )
            ],
            cpu="1",
            memory="2Gi",
            container_configuration=ContainerConfiguration(
                image=args.image_uri
            ),
            environment_variables={
                "AZURE_AI_MODEL_DEPLOYMENT_NAME": args.deployment_name,
            },
        ),
    )

    utils.print_ok(
        f"Agent created: {agent.name}, version: {agent.version}, id: {agent.id}"
    )


if __name__ == "__main__":
    main()