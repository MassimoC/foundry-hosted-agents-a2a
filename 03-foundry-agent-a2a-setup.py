# -----------------------------------------
# Usage:
#
# py .\03-foundry-agent-a2a-setup.py --agent-name test-harness-research --project-endpoint https://mmcx-foundry.services.ai.azure.com/api/projects/mmcx-project
#
# Requirements:
#   pip install "azure-ai-projects>=2.3.0" azure-identity
# -----------------------------------------

import argparse

from azure.identity import AzureCliCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    A2AProtocolConfiguration,
    AgentCard,
    AgentCardSkill,
    AgentEndpointConfig,
    ProtocolConfiguration,
    ResponsesProtocolConfiguration,
)


# --------------------------------------------------
# Configuration
# --------------------------------------------------


AGENT_CARD_DESCRIPTION = """
A research harness that plans and executes multi-step research tasks using web
search and browsing. It validates claims across multiple sources, resolves
conflicting information, tracks citations, and produces structured,
source-backed research reports. Research findings are also persisted to durable
file memory so they can be referenced across the hosted session.
""".strip()


SKILL_NAME = "multi-source research"

SKILL_DESCRIPTION = """
Use web search and browsing to gather authoritative and relevant information,
validate important claims across multiple sources, identify conflicting
evidence, and synthesize the findings into a clear research report with inline
citations.

Use this skill when the user asks to investigate, compare, evaluate, explain,
or produce a researched report on a topic where current or externally
verifiable information is important.
""".strip()


EXAMPLE_PROMPTS = [
    (
        "Research how Kubernetes-based agent runtimes are evolving to support "
        "long-running AI agents. Compare Agent Substrate, KEDA-based scaling, "
        "and traditional Kubernetes StatefulSets. Focus on workload lifetime, "
        "compute allocation, state persistence, scale-to-zero behavior, and "
        "architectural trade-offs."
    )
]


# --------------------------------------------------
# Arguments
# --------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure the A2A card for a Foundry hosted agent."
    )

    parser.add_argument(
        "--agent-name",
        required=True,
        help="Name of the Foundry hosted agent.",
    )

    parser.add_argument(
        "--project-endpoint",
        required=True,
        help="Foundry project endpoint.",
    )
    
    return parser


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    args = build_parser().parse_args()

    credential = AzureCliCredential()

    project = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=credential,
        allow_preview=True,
    )

    patched_agent = project.agents.update_details(
        agent_name=args.agent_name,

        agent_card=AgentCard(
            version="1.0",
            description=AGENT_CARD_DESCRIPTION,
            skills=[
                AgentCardSkill(
                    id="multi-source-research",
                    name=SKILL_NAME,
                    description=SKILL_DESCRIPTION,
                    examples=EXAMPLE_PROMPTS,
                )
            ],
        ),

        agent_endpoint=AgentEndpointConfig(
            protocol_configuration=ProtocolConfiguration(
                responses=ResponsesProtocolConfiguration(),
                a2a=A2AProtocolConfiguration(),
            ),
        ),
    )

    print(f"A2A enabled for agent: {patched_agent.name}")
    print()
    print("A2A agent card configured successfully.")
    print()

    print(
        f"A2A v0.3 agent card URL:\n"
        f"{args.project_endpoint}/agents/{args.agent_name}"
        f"/endpoint/protocols/a2a/agentCard/v0.3"
    )

    print()

    print(
        f"A2A v1.0 agent card URL:\n"
        f"{args.project_endpoint}/agents/{args.agent_name}"
        f"/endpoint/protocols/a2a/agentCard/v1.0"
    )


if __name__ == "__main__":
    main()