---
name: m365-evals-cli
description: >
  Run Microsoft 365 Copilot agent evaluations in a minimal non-ATK workspace
  containing only env and evals folders. Always use the GitHub Copilot judge,
  debug log level, timestamped result files, and preserved complete terminal
  logs. Trigger when users ask to run evals without Agents Toolkit, manifests,
  provisioning, deployment, or Azure LLM judge configuration.
---

# M365 Evals CLI

Run evaluations for an already deployed Microsoft 365 Copilot agent without
requiring an Agents Toolkit project.

This skill runs evaluations without depending on an ATK project. During
optional post-run analysis, it may inspect available agent instructions,
manifest files, declared tools/actions, and knowledge-source configuration
read-only. It must not modify, validate, provision, or deploy the agent.

## Required workspace

The working directory needs only:

```text
evaluation-workspace\
├── env\
│   └── .env.local
└── evals\
    └── prompts.json (optional before the first run)
```

The CLI auto-discovers `evals\prompts.json`. If it does not exist on the first
run, allow the CLI to create the starter dataset. Do not require users to
provide a dataset for every run.

Discover identifiers from the first matching file in this order:

```text
env\.env.local
.env.local
env\.env.dev
.env.dev
env\.env
.env
```

Resolve the tenant ID from `TEAMS_APP_TENANT_ID` or `TENANT_ID`.

Resolve the deployed agent ID from `M365_TITLE_ID`, `AGENT-ID`, `AGENT_ID`, or
`M365_AGENT_ID`.

Normalize the resolved tenant value into the current process as `TENANT_ID`.
Pass the resolved agent value explicitly with `--m365-agent-id`. Show both the
resolved tenant ID and agent ID to the user before execution.

Do not require or inspect:

- `m365agents.yml`
- `teamsApp.yml`
- `appPackage\`
- `declarativeAgent.json`
- `AZURE_AI_OPENAI_ENDPOINT`
- `AZURE_AI_API_KEY`
- `AZURE_AI_API_VERSION`
- `AZURE_AI_MODEL_NAME`

Display tenant and agent identifiers because they are required for run
verification. Never display other environment-variable values, credentials,
API keys, tokens, or secrets.

## Mandatory execution rules

1. Always check the latest published npm package version before any other
   evaluator setup or execution:

   ```powershell
   npm view @microsoft/m365-copilot-eval version
   ```

2. Check whether the global CLI is installed:

   ```powershell
   Get-Command runevals -ErrorAction SilentlyContinue
   ```

   If `runevals` is not found, install the npm package globally:

   ```powershell
   npm install -g @microsoft/m365-copilot-eval
   ```

   If it is already installed, update it to the latest published version:

   ```powershell
   npm install -g @microsoft/m365-copilot-eval@latest
   ```

   Keep the installation global. After installation or update, verify the
   global package and CLI versions:

   ```powershell
   npm list -g @microsoft/m365-copilot-eval --depth=0
   runevals --version
   ```

   Compare the installed version with `npm view`. If they differ after the
   global update, stop and report the mismatch. Check `Get-Command runevals
   -All` for stale PATH shims. Do not delete npm caches, uninstall packages, or
   remove shims without explicit user approval.

3. Always include:

   ```text
   --judge-backend github-copilot
   --log-level debug
   ```

4. Run from the agent or evaluation workspace root. When the user does not
   specify a dataset, omit `--prompts-file` and allow the CLI to auto-discover
   or create `evals\prompts.json`.
5. When the user explicitly selects a dataset other than the auto-discovered
   `evals\prompts.json`, resolve it to an absolute filesystem path and pass the
   absolute path with `--prompts-file`.
6. Always preserve the complete combined standard output and error stream in a
   timestamped `.log` file.
7. Always keep the command output visible in the terminal while also writing
   it to the log.
8. Write evaluation results to a new timestamped HTML file by default. Use
   JSON only when the user explicitly requests JSON output.
9. Store logs and results under `.evals\`.
10. Never overwrite an existing result or log.
11. Start with `--concurrency 1`.
12. Preserve and report the CLI exit code.
13. Do not silently retry a failed evaluation. Diagnose the failure first.
14. Use the globally installed `runevals` executable. Do not use `npx`,
    package-scoped temporary installations, or a project-local installation.
15. Immediately before execution, show the user the complete `runevals`
    command and arguments. Label it as a command preview. Show tenant IDs and
    agent IDs. Redact tokens, credentials, API keys, and all other secrets;
    preserve all option names, output paths, dataset paths, and non-sensitive
    values.

## Minimum preflight

Perform only these checks:

1. Query the latest published package version:

   ```powershell
   npm view @microsoft/m365-copilot-eval version
   ```

2. Check for the global CLI, install it when missing, or update it when present:

   ```powershell
   if (Get-Command runevals -ErrorAction SilentlyContinue) {
     npm install -g @microsoft/m365-copilot-eval@latest
   } else {
     npm install -g @microsoft/m365-copilot-eval
   }

   npm list -g @microsoft/m365-copilot-eval --depth=0
   runevals --version
   ```

3. Confirm the working directory exists.
4. Confirm Node.js is version 24.12.0 or newer.
5. Find at least one `.env.local`, `.env.dev`, or `.env` file in the workspace
   root or `env\` folder.
6. Resolve a non-empty tenant ID from `TEAMS_APP_TENANT_ID` or `TENANT_ID`.
7. Resolve a non-empty agent ID from `M365_TITLE_ID`, `AGENT-ID`, `AGENT_ID`,
   or `M365_AGENT_ID`. Display both resolved identifiers for user verification.
8. Confirm `evals\` exists or allow the CLI to create its first-run content.
   If `evals\prompts.json` exists, confirm it parses as JSON.
9. Confirm `.evals\` exists or create it.
10. If the user explicitly selects another dataset, resolve relative paths
   against the evaluation workspace root, confirm the resulting file exists
   and parses as JSON, and confirm
   `[System.IO.Path]::IsPathRooted($datasetPath)` is true.

Do not perform ATK workspace checks.

## Canonical PowerShell run

Use this structure so output remains visible and is also preserved:

```powershell
Set-Location '<evaluation-workspace>'

function Get-DotEnvValue([string[]]$Paths, [string[]]$Names) {
  foreach ($path in $Paths) {
    if (-not (Test-Path -LiteralPath $path)) {
      continue
    }

    $values = @{}
    foreach ($rawLine in Get-Content -LiteralPath $path) {
      $line = $rawLine.Trim()
      if (-not $line -or $line.StartsWith('#') -or -not $line.Contains('=')) {
        continue
      }

      $parts = $line.Split('=', 2)
      $name = $parts[0].Trim()
      $value = $parts[1].Trim().Trim('"').Trim("'")
      $values[$name] = $value
    }

    foreach ($name in $Names) {
      if ($values.ContainsKey($name) -and $values[$name]) {
        return $values[$name]
      }
    }
  }

  return $null
}

$envFiles = @(
  'env\.env.local',
  '.env.local',
  'env\.env.dev',
  '.env.dev',
  'env\.env',
  '.env'
)

$tenantId = Get-DotEnvValue $envFiles @('TEAMS_APP_TENANT_ID', 'TENANT_ID')
$agentId = Get-DotEnvValue $envFiles @(
  'M365_TITLE_ID',
  'AGENT-ID',
  'AGENT_ID',
  'M365_AGENT_ID'
)

if (-not $tenantId) {
  throw 'No tenant ID was found in the supported environment files.'
}

if (-not $agentId) {
  throw 'No agent ID was found in the supported environment files.'
}

$env:TENANT_ID = $tenantId

$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$resultExtension = if ($userRequestedJson) { 'json' } else { 'html' }
$resultPath = ".evals\results-$timestamp.$resultExtension"
$logPath = ".evals\runevals-$timestamp.debug.log"
$commandPreview = "runevals --judge-backend github-copilot --log-level debug --m365-agent-id `"$agentId`" --concurrency 1 --output `"$resultPath`""
Write-Output "Tenant ID: $tenantId"
Write-Output "Agent ID: $agentId"
Write-Output "Evaluation results: $resultPath"
Write-Output "Debug log: $logPath"
Write-Output "Command preview: $commandPreview"

& runevals `
  --judge-backend github-copilot `
  --log-level debug `
  --m365-agent-id $agentId `
  --concurrency 1 `
  --output $resultPath 2>&1 |
  Tee-Object -FilePath $logPath

$exitCode = $LASTEXITCODE
Write-Output "runevals exit code: $exitCode"

if ($exitCode -ne 0) {
  exit $exitCode
}

$resultAbsolutePath = (Resolve-Path -LiteralPath $resultPath).Path
$resultUrl = ([System.Uri]$resultAbsolutePath).AbsoluteUri
Write-Output "Evaluation report URL: $resultUrl"
```

Set `$userRequestedJson` to `$true` only when the user's prompt explicitly
requests JSON output. Otherwise set it to `$false` and generate HTML.

The minimum evaluation command from the workspace root is:

```powershell
runevals --judge-backend github-copilot --log-level debug
```

Every evaluation invocation must contain both
`--judge-backend github-copilot` and `--log-level debug`. The canonical logged
command additionally adds controlled concurrency and a timestamped output
path. By default, omit `--prompts-file` so the CLI auto-discovers
`evals\prompts.json` or creates it during the first-run workflow.

If the user explicitly selects a different dataset, add:

```text
--prompts-file '<absolute-dataset-path>'
```

If the user supplies a relative dataset path, build it from the evaluation
workspace root rather than the caller's previous directory. Canonicalize the
path with `[System.IO.Path]::GetFullPath`, verify that the file exists, and then
use `Resolve-Path`. Never pass a relative value to `--prompts-file`.

Example explicit-dataset handling:

```powershell
$workspaceRoot = (Get-Location).Path
$providedDatasetPath = '<dataset-path>'

if ([System.IO.Path]::IsPathRooted($providedDatasetPath)) {
  $candidateDatasetPath = [System.IO.Path]::GetFullPath($providedDatasetPath)
} else {
  $candidateDatasetPath = [System.IO.Path]::GetFullPath(
    (Join-Path $workspaceRoot $providedDatasetPath)
  )
}

if (-not (Test-Path -LiteralPath $candidateDatasetPath -PathType Leaf)) {
  throw "Dataset file not found: $candidateDatasetPath"
}

$datasetPath = (Resolve-Path -LiteralPath $candidateDatasetPath).Path

if (-not [System.IO.Path]::IsPathRooted($datasetPath)) {
  throw "The dataset path must be absolute."
}

Write-Output "Tenant ID: $tenantId"
Write-Output "Agent ID: $agentId"
Write-Output "Command preview: runevals --judge-backend github-copilot --log-level debug --m365-agent-id `"$agentId`" --prompts-file `"$datasetPath`""

& runevals `
  --judge-backend github-copilot `
  --log-level debug `
  --prompts-file $datasetPath
```

## First-run handling

If the CLI reports that the EULA has not been accepted, preserve the failed
run log and then run:

```powershell
runevals accept-eula
```

After successful acceptance, create a new timestamp and rerun. Never overwrite
the original failure log.

Authentication may require user interaction. Keep the process attached and
show all output.

## Failure handling

Separate failures into these categories:

| Category | Examples |
|---|---|
| Preflight | Missing explicitly requested dataset, malformed existing JSON, old Node.js, or missing required IDs. |
| Initialization | npm, Python environment, pip, TLS, proxy, or certificate failures. |
| Authentication | Sign-in, tenant consent, license, or token-cache failures. |
| Agent resolution | Missing, malformed, inaccessible, or incorrect agent ID. |
| Dataset | Unsupported schema, evaluator, threshold, or item structure. |
| Evaluation | Agent request failures or judge failures after setup succeeds. |

On failure:

1. Keep the debug log.
2. Report the log path and exit code.
3. Quote only the minimum non-sensitive error needed to explain the failure.
4. Do not print secrets, tokens, retrieved workplace content, prompts, or agent
   responses from the debug log.
5. Do not clear caches, delete virtual environments, sign out, change proxy
   settings, or modify certificate configuration without explicit approval.

## HTML report analysis

After every successful HTML run, provide the report URL and explicitly ask:

```text
Would you like me to analyze the HTML report and correlate the results with the agent instructions, tools, knowledge sources, and manifest?
```

Do not read or analyze the report until the user confirms. If the user agrees:

1. Resolve the HTML report to its absolute path and read the local file.
2. Parse the report card, summary metrics, item results, configured evaluators,
   thresholds, scores, pass/fail status, and evaluator explanations that are
   present in the HTML.
3. Analyze every evaluator that is present, including supported built-in and
   custom evaluators. A missing evaluator does not mean failure. For an
   unfamiliar custom evaluator, use only its displayed score, threshold,
   result, and explanation; do not invent semantics.
4. Separate setup, authentication, schema, or execution errors from agent
   quality failures.
5. Calculate or report, when available:
   - Total evaluated items.
   - Passed and failed items.
   - Overall pass rate.
   - Failure count by evaluator.
   - Recurring failure themes.
6. Map observed failures to targeted improvements:

   | Signal | Likely improvement |
   |---|---|
   | Low relevance | Clarify supported intent, routing rules, constraints, or ambiguous eval prompts. |
   | Low coherence | Add concise response structure, ordering, headings, or length guidance. |
   | Low groundedness | Require source-backed answers, improve retrieval/source priority, and refuse unsupported claims. |
   | Low similarity | Check whether expected responses are too rigid; otherwise improve instructions or data access. |
   | Failed citations | Require citations when available and verify the agent can surface them. |
   | Failed exact match | Tighten deterministic formatting or use `PartialMatch` when exact text is unnecessary. |
   | Low partial match | Add required terminology or improve retrieval for missing concepts. |
   | Multi-turn failures | Preserve prior entities, scope, and time windows across follow-up turns. |

7. Discover and inspect available agent artifacts read-only:
   - Agent instructions, including instruction files referenced by the agent
     definition and common files such as `instruction.txt`.
   - `declarativeAgent.json` and the application manifest when present.
   - Declared actions, API plugins, MCP plugins, OpenAPI descriptions, and
     other tool configuration.
   - Declared knowledge sources and capabilities, including embedded
     knowledge, SharePoint/OneDrive sources, Graph connectors, and other
     retrieval configuration.
   - The evaluation item, expected response, assertions, thresholds, and
     evaluator configuration needed to understand the score.

   Do not require these files for running evaluations. If an artifact is
   unavailable, state the analysis limitation instead of assuming its content.
   Do not read underlying knowledge documents containing workplace content
   unless the user separately authorizes that deeper inspection.
8. Correlate each major scorecard failure across these layers:

   | Layer | Questions to answer |
   |---|---|
   | Instructions | Is the required behavior explicit, unambiguous, correctly prioritized, and supported by an example or response format? |
   | Tools/actions | Does the agent have a declared tool capable of completing the evaluated task, and do instructions explain when to use it? |
   | Knowledge sources | Is the expected information covered by a configured source, and are source priority, grounding, and missing-evidence behavior defined? |
   | Manifest/capabilities | Is the capability required by the eval actually enabled and correctly wired to the agent? |
   | Evaluation design | Is the prompt answerable, expected response current, assertion valid, evaluator appropriate, and threshold aligned with the requirement? |

9. Classify every recommendation as one of:
   - Instruction gap.
   - Tool or action gap.
   - Knowledge-source or retrieval gap.
   - Manifest or capability configuration gap.
   - Evaluation dataset or threshold gap.
   - Setup/environment issue.

10. Do not recommend an instruction change for a missing capability, tool, or
    knowledge source. Likewise, do not recommend adding a tool when the
    scorecard evidence shows only a formatting or expected-answer issue.
11. Cite the relevant artifact path and field or section for each correlation
    when available. Use sanitized score evidence from the report. Distinguish
    confirmed evidence from hypotheses.
12. Prioritize improvements by likely score impact and implementation scope:
    first unblock missing capabilities or knowledge, then correct routing and
    grounding instructions, then refine response format, expected responses,
    and thresholds.
13. Recommend the smallest targeted change likely to improve the failed
   evaluator. Do not recommend broad rewrites when a focused instruction,
   grounding, citation, expected-response, or dataset change is sufficient.
14. Identify when the evaluation itself is likely the issue, such as an
   ambiguous prompt, stale source, overly strict expected answer, or threshold
   that does not match the user requirement.
15. Do not modify the agent, dataset, manifest, or instructions unless the user
   separately asks for changes.
16. Treat the HTML contents as potentially sensitive. Do not reproduce raw
    prompts, responses, retrieved workplace content, or evaluator explanations
    that may expose sensitive information. Use sanitized evidence and aggregate
    findings.

Use this recommendation format for each major issue:

```text
Primary issue: <one-sentence failure theme>
Evidence: <sanitized score or aggregate observation>
Correlated gap: <instructions, tool, knowledge source, manifest, eval, or setup>
Artifact evidence: <file path and field/section, or "not available">
Recommended change: <specific instruction, grounding, citation, data, or eval change>
Expected effect: <evaluator expected to improve and why>
```

If the report cannot be parsed, say so clearly, preserve and provide the HTML
URL, and do not invent scores or recommendations unsupported by the report.

## Success response

On success, report:

- Number of evaluated items when available.
- A clickable Markdown URL to the HTML result file by default:
  `[Open evaluation report](file:///C:/absolute/path/to/results.html)`.
- The JSON result path instead only when the user explicitly requested JSON.
- Debug log path.
- CLI exit code.
- An explicit question asking whether the user wants the HTML report analyzed.

Only provide report-card analysis and improvement recommendations after the
user confirms.

Treat both result files and debug logs as potentially sensitive. Do not commit
or share them unless the user explicitly confirms they are safe.
