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

evidence

<img width="1540" height="116" alt="image" src="https://github.com/user-attachments/assets/6892bde5-5c46-4954-ae66-996e5001e501" />

expected result

<img width="789" height="400" alt="image" src="https://github.com/user-attachments/assets/f233c14b-fa36-42f3-892f-e143b6e2eba8" />

**STEP 2 : deploy on Foundry Hosted Agents**

```
py .\02-foundry-agent-deploy.py `
   --agent-name test-harness-research `
   --project-endpoint https://mmcx-foundry.services.ai.azure.com/api/projects/mmcx-project `
   --deployment-name gpt-5.6-luna `
   --image-uri mmcxacr.azurecr.io/harness-research:91 `
   --description "A research harness agent with web search, planning, todos, and compaction."
```

evidence

<img width="913" height="134" alt="image" src="https://github.com/user-attachments/assets/a584dbda-1f4d-45e5-ad6a-c2933cb20b7f" />

expected result

<img width="1503" height="257" alt="image" src="https://github.com/user-attachments/assets/00c06fcc-238d-47c3-af0f-f9872690d5e0" />

**STEP 3 : setup A2A endpoint**

```  
py .\03-foundry-agent-a2a-setup.py --agent-name test-harness-research --project-endpoint "https://mmcx-foundry.services.ai.azure.com/api/projects/mmcx-project"
```

evidence

<img width="2067" height="191" alt="image" src="https://github.com/user-attachments/assets/431a9693-c084-44a6-9264-32561bbe7b69" />

expected result

<img width="831" height="537" alt="image" src="https://github.com/user-attachments/assets/6dbe5ced-d7f6-400a-9eb3-83e851be5247" />

**STEP 4 : get the agent card**

```  
py .\04-foundry-a2a-test-raw-syncasync.py "here the text" --agent-name test-harness-research --agent-card-path agentCard/v1.0 --card-only
```

evidence

<img width="2021" height="1134" alt="image" src="https://github.com/user-attachments/assets/7bcc67a8-ac7d-48d2-a353-ee482f437606" />

**STEP 5 : call the A2A endpoint**

```  
py .\04-foundry-a2a-test-raw-syncasync.py "cloud hybervisor vs hyperlight. do not ask user for additional approval, just execute your plan" --agent-name test-harness-research --agent-card-path agentCard/v1.0
```

<img width="1476" height="850" alt="image" src="https://github.com/user-attachments/assets/0a2493f1-8ea0-45d0-8166-59772383e56c" />
