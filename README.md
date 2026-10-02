# foundry-hosted-agents-a2a
Test the foundry A2A implementation.

## Prerequisites

* Foundry project
* Azure Container Registry

## Reproduce

**STEP 1 : build the container image**

Build the `19-harness-research` sample referencing the GH example : https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework/responses/19-harness-research/src/agent-framework-harness-research-responses

```
py .\01-foundry-agent-build.py --name harness-research --build-version 91 --registry mmcxacr
```

command

expected result


**STEP 2 : deploy on Foundry Hosted Agents**

```
py .\02-foundry-agent-deploy.py `
   --agent-name test-harness-research `
   --project-endpoint https://mmcx-foundry.services.ai.azure.com/api/projects/mmcx-project `
   --deployment-name gpt-5.6-luna `
   --image-uri mmcxacr.azurecr.io/harness-research:91 `
   --description "A research harness agent with web search, planning, todos, and compaction."
```

command

expected result

**STEP 3 : setup A2A endpoint**

```  
py .\03-foundry-agent-a2a-setup.py --agent-name test-harness-research --project-endpoint "https://mmcx-foundry.services.ai.azure.com/api/projects/mmcx-project"
```

command

expected result


**STEP 4 : test**
```  
py .\04-foundry-a2a-test-raw-syncasync.py "here the text" --agent-name test-harness-research --agent-card-path agentCard/v1.0 --card-only
```

command

observation

