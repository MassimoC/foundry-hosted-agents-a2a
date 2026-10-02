# -----------------------------------------
# Usage:
#
# py .\01-foundry-agent-build.py --name harness-research --build-version 111 --registry mmcxacr
#
# Examples:
#   py .\01-foundry-agent-build.py --name harness-research --build-version 100
# -----------------------------------------

import argparse
import os
import sys

import utils




def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and push a Foundry hosted agent container image."
    )

    parser.add_argument(
        "--name",
        required=True,
        default=os.environ.get("NAME", "harness-research"),
        help="Agent name.",
    )

    parser.add_argument(
        "--build-version",
        type=int,
        default=1,
        help="Agent build version. Defaults to 1.",
    )

    parser.add_argument(
        "--registry",
        default=os.environ.get("ACR_REGISTRY", "mmcxacr"),
        help="ACR registry name. Defaults to ACR_REGISTRY or 'mmcxacr'.",
    )

    return parser


def run(args) -> str:
    utils.print_info(f"hola")
    
    agent_name = args.name
    build_version = args.build_version
    container_registry_name = args.registry
    
    agent_image_tag = f"{agent_name}:{build_version}"
    
    agent_src = "https://github.com/microsoft-foundry/foundry-samples.git#main:samples/python/hosted-agents/agent-framework/responses/19-harness-research/src/agent-framework-harness-research-responses"

    # Azure CLI on Windows can fail while streaming ACR build logs if the
    # output contains Unicode characters that cannot be encoded using the
    # default Windows code page (for example cp1252).
    #
    # Setting these variables here ensures that the Azure CLI child process
    # inherits UTF-8 settings, regardless of whether utils.run() ultimately
    # uses PowerShell, cmd.exe, or subprocess.
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    utils.print_info(
        f"Building '{agent_name}' agent image: {agent_image_tag}"
    )

    utils.run(
        f'az acr build '
        f'--registry "{container_registry_name}" '
        f'--image "{agent_image_tag}" '
        f'-f Dockerfile "{agent_src}"',
        f"'{agent_name}' agent image built and pushed: {agent_image_tag}",
        f"Failed to build and push the '{agent_name}' agent image",
    )
    


    image_uri = (
        f"{container_registry_name}.azurecr.io/"
        f"{agent_image_tag}"
    )

    utils.print_info(f"Image URI: {image_uri}")

    return image_uri


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        run(args)
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:  # noqa: BLE001
        print(
            f"ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()