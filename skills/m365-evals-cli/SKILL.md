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

This skill runs evaluations only. It must not inspect, validate, modify,
provision, deploy, or otherwise depend on an ATK project.

## Required workspace

The working directory needs only:

```text
evaluation-workspace\
├── env\
│   └── .env.local
└── evals\
    └── <dataset>.json
```

The `env\.env.local` file must define:

```dotenv
TEAMS_APP_TENANT_ID=<tenant-guid>
M365_TITLE_ID=<deployed-agent-title-id>
```

Also accept `TENANT_ID` as a fallback for `TEAMS_APP_TENANT_ID`, and
`M365_AGENT_ID` as an alternative to `M365_TITLE_ID`.

Do not require or inspect:

- `m365agents.yml`
- `teamsApp.yml`
- `appPackage\`
- `declarativeAgent.json`
- `AZURE_AI_OPENAI_ENDPOINT`
- `AZURE_AI_API_KEY`
- `AZURE_AI_API_VERSION`
- `AZURE_AI_MODEL_NAME`

Never display environment-variable values.

## Mandatory execution rules

1. Always check the latest published npm package version before any other
   evaluator setup or execution:

   ```powershell
   npm view @microsoft/m365-copilot-eval version
   ```

2. Always install or update the global package to the latest published version:

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

4. Run from the agent or evaluation workspace root and let `runevals`
   auto-discover the `env\` and `evals\` folders by default.
5. Always preserve the complete combined standard output and error stream in a
   timestamped `.log` file.
6. Always keep the command output visible in the terminal while also writing
   it to the log.
7. Always write evaluation results to a new timestamped JSON file.
8. Store logs and results under `.evals\`.
9. Never overwrite an existing result or log.
10. Start with `--concurrency 1`.
11. Preserve and report the CLI exit code.
12. Do not silently retry a failed evaluation. Diagnose the failure first.
13. Use the globally installed `runevals` executable. Do not use `npx`,
    package-scoped temporary installations, or a project-local installation.

## Minimum preflight

Perform only these checks:

1. Query the latest published package version:

   ```powershell
   npm view @microsoft/m365-copilot-eval version
   ```

2. Install or update the global package and confirm its CLI version:

   ```powershell
   npm install -g @microsoft/m365-copilot-eval@latest
   npm list -g @microsoft/m365-copilot-eval --depth=0
   runevals --version
   ```

3. Confirm the working directory exists.
4. Confirm Node.js is version 24.12.0 or newer.
5. Confirm `env\.env.local` exists.
6. Confirm the environment file contains a non-empty tenant ID in either
   `TEAMS_APP_TENANT_ID` or `TENANT_ID`, and an agent ID in either
   `M365_TITLE_ID` or `M365_AGENT_ID`, without displaying their values.
7. Confirm at least one supported JSON dataset exists under `evals\` and parses
   as JSON. If the user specifies a dataset, validate that exact file.
8. Confirm `.evals\` exists or create it.

Do not perform ATK workspace checks.

## Canonical PowerShell run

Use this structure so output remains visible and is also preserved:

```powershell
Set-Location '<evaluation-workspace>'

$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$resultPath = ".evals\results-$timestamp.json"
$logPath = ".evals\runevals-$timestamp.debug.log"

Write-Output "Evaluation results: $resultPath"
Write-Output "Debug log: $logPath"

& runevals `
  --judge-backend github-copilot `
  --log-level debug `
  --concurrency 1 `
  --output $resultPath 2>&1 |
  Tee-Object -FilePath $logPath

$exitCode = $LASTEXITCODE
Write-Output "runevals exit code: $exitCode"

if ($exitCode -ne 0) {
  exit $exitCode
}
```

The minimum evaluation command from the workspace root is:

```powershell
runevals --judge-backend github-copilot
```

## Canonical macOS and Linux run

Use this structure in Bash or Zsh:

```bash
cd '<evaluation-workspace>'

timestamp="$(date '+%Y-%m-%d_%H-%M-%S')"
result_path=".evals/results-$timestamp.json"
log_path=".evals/runevals-$timestamp.debug.log"

echo "Evaluation results: $result_path"
echo "Debug log: $log_path"

set -o pipefail
runevals \
  --judge-backend github-copilot \
  --log-level debug \
  --concurrency 1 \
  --output "$result_path" 2>&1 | tee "$log_path"

exit_code=${PIPESTATUS[0]}
echo "runevals exit code: $exit_code"

if [ "$exit_code" -ne 0 ]; then
  exit "$exit_code"
fi
```

The canonical logged command adds only debug logging, controlled concurrency,
and a timestamped output path. Let the CLI auto-discover the environment and
dataset. If the user explicitly supplies a dataset, add:

```text
--prompts-file '<dataset-path>'
```

Use an absolute dataset path exactly as supplied after confirming it exists.

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
| Preflight | Missing dataset, malformed JSON, old Node.js, missing required IDs. |
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

## Success response

On success, report:

- Number of evaluated items when available.
- Result JSON path.
- Debug log path.
- CLI exit code.

Treat both result files and debug logs as potentially sensitive. Do not commit
or share them unless the user explicitly confirms they are safe.
