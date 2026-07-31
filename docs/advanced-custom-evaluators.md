# Advanced guide: Custom evaluators and GPT-5 Foundry judges

This guide contains two advanced paths:

1. Run the Zava `AssertionJudge` Prompty custom evaluator with an Azure OpenAI
   judge.
2. Run a code-only answer-length evaluator alongside GPT-5.x built-in judges
   through Microsoft Foundry cloud evaluation.

These paths are separate because the current eval CLI routes only the built-in
LLM evaluators (`Relevance`, `Coherence`, `Groundedness`, and `Similarity`)
through Foundry cloud evaluation. User-authored Prompty evaluators such as
`AssertionJudge` still use the local Azure OpenAI model configuration.

## Track A: Run the Zava AssertionJudge custom evaluator

### A1. Review the included files

The existing custom-evaluator folder is included at:

```text
zava-insurance-claims/custom-evaluators/AssertionJudge/
├── AssertionJudge.py
└── AssertionJudge.prompty
```

The advanced Zava dataset is:

```text
zava-insurance-claims/evals/zava-insurance-claims.json
```

The dataset contains 12 scenarios and references `AssertionJudge` on individual
items. It also uses `Similarity` and `Groundedness` as defaults.

The folder name, Python filename, Prompty filename, and evaluator name must
match exactly. The presence of `AssertionJudge.prompty` tells the CLI this is
an LLM-based custom evaluator.

### A2. Configure an Azure OpenAI judge

Prompty custom evaluators require Azure OpenAI configuration. Add the following
to the environment file used by the Zava workspace:

```dotenv
M365_TITLE_ID="T_your-title-id-here"
TEAMS_APP_TENANT_ID="your-tenant-id"
AZURE_AI_OPENAI_ENDPOINT="https://<resource>.openai.azure.com/"
AZURE_AI_MODEL_NAME="<supported-gpt-4x-deployment-name>"
AZURE_AI_API_VERSION="2024-12-01-preview"
```

Authenticate using either:

- `AZURE_AI_API_KEY` in a local, ignored environment file, or
- `DefaultAzureCredential` after `az login`, with the required Azure role.

Do not commit keys or tenant-specific environment files.

> **Current limitation:** Do not configure this Prompty evaluator with a
> GPT-5.x or o-series deployment. Those models require Foundry cloud
> evaluation, and custom Prompty evaluators are not currently routed through
> that path. Use a supported GPT-4.x deployment for `AssertionJudge`.

### A3. Ask Copilot CLI to run the dataset

From Copilot CLI, enter:

```text
Can you run an evaluation for the zava-insurance-claims agent using the evals CLI and the dataset "C:\Users\sakov\bootcamp\zava-insurance-claims\evals\zava-insurance-claims.json"? This dataset uses the AssertionJudge custom evaluator, so use the Azure judge configuration.
```

Replace the absolute path if the repository is cloned elsewhere. On macOS and
Linux, use the corresponding forward-slash path.

### A4. Run the dataset directly

**Windows (PowerShell):**

```powershell
cd .\zava-insurance-claims
$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
runevals `
  --env local `
  --prompts-file .\evals\zava-insurance-claims.json `
  --concurrency 1 `
  --output ".\.evals\assertion-judge-$timestamp.html"
```

**macOS and Linux:**

```bash
cd ./zava-insurance-claims
timestamp="$(date '+%Y-%m-%d_%H-%M-%S')"
runevals \
  --env local \
  --prompts-file ./evals/zava-insurance-claims.json \
  --concurrency 1 \
  --output "./.evals/assertion-judge-$timestamp.html"
```

Do not add `--judge-backend github-copilot` to this run. The
`AssertionJudge` Prompty evaluator requires the Azure model configuration.

## Track B: Run a code evaluator with a GPT-5 Foundry judge

This track combines:

- `Relevance` and `Coherence`, evaluated by GPT-5 in Microsoft Foundry.
- `answer_length`, evaluated locally with deterministic Python code.

## 1. Understand the two custom-evaluator types

| Type | Files | Model requirement | GitHub Copilot judge |
|---|---|---|---|
| Code-only | `<name>.py` | No model call | Supported |
| Prompty-based LLM | `<name>.py` and `<name>.prompty` | Azure OpenAI model configuration | Not currently routed through the GitHub Copilot judge |

This tutorial uses a code-only evaluator so it can run alongside Foundry cloud
evaluation without making an additional LLM call.

## 2. Review the included answer-length evaluator

The evaluator is included at:

```text
zava-insurance-claims/custom-evaluators/answer_length/answer_length.py
```

```python
class AnswerLengthEvaluator:
    def __init__(self, **_):
        pass

    def __call__(self, *, response: str = "", **_) -> dict:
        length = len(response)
        return {
            "score": length,
            "reason": f"Agent response contains {length} characters.",
        }
```

The folder, Python filename, and evaluator name must match exactly:
`answer_length`. Do not add an `answer_length.prompty` file; its absence tells
the CLI that this is a code-only evaluator.

The evaluator returns a numeric `score` and a `reason`. The eval CLI attaches
the configured threshold and derives pass/fail.

## 3. Review the advanced dataset

The sample dataset is:

```text
zava-insurance-claims/evals/custom-answer-length-gpt5.json
```

It configures the custom evaluator for every item through
`default_evaluators`:

```json
{
  "default_evaluators": {
    "Relevance": {},
    "Coherence": {},
    "answer_length": {
      "threshold": 1
    }
  }
}
```

The score is the number of characters in the agent response. A threshold of
`1` means any non-empty response passes while the report preserves the actual
character count.

## 4. Create or select a Microsoft Foundry project

GPT-5.x and o-series judge models cannot use the eval CLI's default local
evaluator path. They require Microsoft Foundry cloud evaluation.

Prepare:

1. A Microsoft Foundry project.
2. A chat-capable GPT-5.x or o-series model deployment, such as
   `gpt-5-mini`.
3. The **Azure AI Developer** role on the Foundry project.
4. Azure CLI authentication through Microsoft Entra.

From the Foundry project, copy the project endpoint. It has this form:

```text
https://<account>.services.ai.azure.com/api/projects/<project>
```

The project endpoint is shown on the Foundry project home page:

![Microsoft Foundry project endpoint highlighted on the project home page](images/gpt5-screen-1.png)

Under **Recent work**, select the GPT-5 deployment that you want to use:

![GPT-5 mini deployment highlighted under Recent work](images/gpt5-screen-2.png)

On the deployment's **Details** tab, copy the deployment **Name**:

![GPT-5 mini deployment name highlighted on the Details tab](images/gpt5-screen-3.png)

Use this deployment name for `AZURE_AI_MODEL_NAME`; do not use only the base
model family unless it exactly matches the deployment name.

## 5. Sign in to Azure

**Windows, macOS, and Linux:**

```text
az login
```

If the Foundry project is in a different tenant:

```text
az login --tenant <tenant-id>
```

The Foundry cloud path uses Entra authentication through
`DefaultAzureCredential`. `AZURE_AI_API_KEY` is not used.

## 6. Configure the Foundry judge

Add these values to the environment file used by the evaluation workspace,
such as `zava-insurance-claims/env/.env.local`:

```dotenv
M365_TITLE_ID="T_your-title-id-here"
TEAMS_APP_TENANT_ID="your-tenant-id"
AZURE_AI_PROJECT_ENDPOINT="https://myacct.services.ai.azure.com/api/projects/myproj"
AZURE_AI_MODEL_NAME="gpt-5-mini"
```

If Azure CLI defaults to a different tenant from the Foundry project, also
set:

```dotenv
AZURE_TENANT_ID="your-foundry-project-tenant-id"
```

Do not commit tenant-specific environment files.

## 7. How judge selection works

When both `AZURE_AI_PROJECT_ENDPOINT` and `AZURE_AI_MODEL_NAME` are set, the
built-in LLM evaluators run through Microsoft Foundry cloud evaluation.

| `AZURE_AI_PROJECT_ENDPOINT` | Supported judge models |
|---|---|
| Set | GPT-5.x, o-series, and GPT-4.x through Microsoft Foundry |
| Unset | GPT-4.x only through the local evaluator path |

For this advanced run, omit `--judge-backend github-copilot`. The Foundry
project and model variables select the GPT-5 judge.

Microsoft Foundry has deprecated GPT-4.x/GPT-4o judge models, with retirement
dates through 2026. Plan to use a GPT-5.x deployment.

## 8. Run the advanced evaluation

Change to the agent project:

**Windows (PowerShell):**

```powershell
cd .\zava-insurance-claims
$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
runevals `
  --env local `
  --prompts-file .\evals\custom-answer-length-gpt5.json `
  --concurrency 1 `
  --output ".\.evals\custom-gpt5-$timestamp.html"
```

**macOS and Linux:**

```bash
cd ./zava-insurance-claims
timestamp="$(date '+%Y-%m-%d_%H-%M-%S')"
runevals \
  --env local \
  --prompts-file ./evals/custom-answer-length-gpt5.json \
  --concurrency 1 \
  --output "./.evals/custom-gpt5-$timestamp.html"
```

The report should contain `Relevance`, `Coherence`, and `answer_length`.

## 9. Analyze or open the scorecard

Users can ask Copilot CLI to analyze the generated report:

```text
Analyze the latest evaluation scorecard under .evals. Summarize pass rates, failed prompts, evaluator reasons, and recommended next steps.
```

Alternatively, open the generated HTML report in a browser and review the
scorecard directly. The report contains aggregate results and a detailed card
for each prompt and evaluator.

Treat reports as potentially sensitive because they can contain prompts, agent
responses, assertions, citations, and retrieved content.

## 10. Add the evaluator to another dataset

Add it to `default_evaluators` to apply it to every item:

```json
"default_evaluators": {
  "Relevance": {},
  "Coherence": {},
  "answer_length": {
    "threshold": 1
  }
}
```

Or add it to one item:

```json
"evaluators": {
  "answer_length": {
    "threshold": 1
  }
},
"evaluators_mode": "extend"
```

## 11. Troubleshooting

| Symptom | Resolution |
|---|---|
| `Unknown evaluator 'answer_length'` | Run from the `zava-insurance-claims` root and confirm the folder and file are both named `answer_length`. |
| `evaluatorLoadError` | Check Python syntax and ensure the module exports a top-level class. |
| `invalidEvaluatorResult` | Return a dictionary containing a numeric `score` and a string `reason`. |
| GPT-5 fails on `response_format` | `AZURE_AI_PROJECT_ENDPOINT` is absent or wasn't loaded. GPT-5 must use Foundry cloud evaluation. |
| Azure 401 or 403 | Run `az login`, confirm the tenant, and verify the **Azure AI Developer** role on the Foundry project. |
| Foundry deployment not found | Confirm `AZURE_AI_MODEL_NAME` exactly matches the deployment name in the project. |
| Custom Prompty evaluator is skipped with GitHub Copilot | Prompty-based custom evaluators are not currently routed through `--judge-backend github-copilot`. Use the Azure path appropriate for that evaluator. |

## References

- [Custom evaluators](https://learn.microsoft.com/azure/foundry-classic/concepts/evaluation-evaluators/custom-evaluators)
- [Microsoft Foundry cloud evaluation](https://learn.microsoft.com/azure/foundry/how-to/develop/cloud-evaluation)
- [Foundry model retirement schedule](https://learn.microsoft.com/azure/foundry/openai/concepts/model-retirement-schedule)
