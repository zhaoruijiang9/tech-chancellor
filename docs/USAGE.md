# User Guide

## Basic Commands

Run from the checkout root with Python 3.11+. A virtual environment is recommended; no third-party Python dependencies are required.

```powershell
python run.py init
python run.py health
python run.py build-library
python run.py my-capabilities
python run.py activation-status
python run.py migrate-capabilities
python run.py check-upstream
python run.py dashboard --browser
```

The first scan can use `python run.py scan --config config/discovery.quickstart.json --dry-run`. Public reads are request-bounded, subject to GitHub rate limits and recorded separately from final review. `--dry-run` does not mean no local writes: scan evidence and pending packets may be persisted. It does mean no third-party installation or execution.

The dashboard binds only to `127.0.0.1`. For scripted checks use `python run.py dashboard --no-browser --port 8766`. The desktop launcher starts the same local server in an app-style browser window. `python run.py install-shortcut` explicitly creates a desktop shortcut; initialization does not.

## Codex and Models

Install and authenticate Codex CLI separately. Set `PTI_CODEX_EXE` to an executable path if it is not on PATH. Formal Stage B uses the existing read-only, ephemeral, schema-constrained CLI invocation.

Model precedence:

1. `PTI_STAGE_B_MODEL` environment variable.
2. Ignored `config/stage_b.local.json`.
3. Legacy ignored `config/stage_b.json` (existing users keep their choice).
4. Codex CLI's own configured default; no model name is shipped as a required default.

Copy `config/stage_b.example.json` to `config/stage_b.local.json` and set `model` only if an override is necessary. Missing CLI is reported as `CODEX_NOT_CONFIGURED`. Authentication, model and service failures preserve the pending packet and expose the actual error; no fallback fabricates a final decision.

GitHub CLI is not required for public reads. `GH_TOKEN` or `GITHUB_TOKEN` may be supplied through the environment. Health distinguishes anonymous reads and configured authentication without disclosing credentials.

## Local State

`init` creates runtime folders, the SQLite database and an UNKNOWN capability profile, preserving an existing profile. `config/capability_usage_defaults.json` contains generic guidance, not ownership or approval. Optional ignored `config/human_capability_usage.json` overrides guidance for the current user.

Readiness is read from the current SQLite `activation_readiness` state. `python run.py activation-readiness` never seeds author decisions from a shipped audit result. With no reviewed sources it returns an empty inventory. Installation manifests, pointers, receipts and personal reports are ignored. `templates/managed-capability.example.json` is disabled and not an installation.

## Scheduling

Windows Scheduler is optional. The scheduled scripts do not register tasks themselves. To opt in, create a Windows Task Scheduler task explicitly, set its working directory to your checkout and point its action at the chosen `run_scheduled_*.ps1` or `.cmd` script. Choose your own schedule and account. Disable or delete that task to revoke scheduling.

Review script side effects first: a scheduled scan may trigger the separately installed Chancellor task, and Chancellor may invoke the bounded activation worker. Do not create tasks on first install merely to make health appear green. Missing tasks are `NOT_INSTALLED`, not a base-product failure.

## Upgrade

Before updating from v0.1.0, stop your own background runs and copy `state/`, `managed_capabilities/`, `user_artifacts/` and ignored/local config to a backup directory **outside the checkout**. Some old releases tracked installation manifests; Git may remove them when advancing to v0.2.0. Restore those specific local files from your backup after updating. Do not overwrite newer user data or delete the database.

Then run `python run.py init` and `python run.py migrate-capabilities`. Initialization updates schema idempotently and retains valid history; capability migration projects reviewed sources in the current user's database, never author defaults. Verify `health`, `activation-status` and the dashboard before re-enabling schedules. SQLite integrity and a published v0.1-compatible schema are covered by release tests.

## Advanced and Maintenance

`python run.py stage-b OWNER/REPO --limit 1` reviews only an existing official packet; it needs Codex.

For a known historical handoff problem, first run `python run.py repair-stranded-candidates OWNER/REPO`. Inspect the dry-run result; only then add `--apply` to resume that one identity. This is a maintenance tool, not a first-install step or a bulk rediscovery command.

`python run.py activation-run --limit 1` uses the current worker and existing safety adapters, not arbitrary executable third-party packages. `python run.py activation-search QUERY` reads only an already validated local index. An empty installation has no active index.

## Development Checks

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests
python -m compileall -q src tests run.py scripts
node --check src/pti/dashboard_assets/app.js
python scripts/release_audit.py
git diff --check
```

Node is optional for JS syntax checks, not the Python dashboard runtime. Publication audit checks the indexed or specified committed tree and all blobs introduced since v0.1.0; findings contain locations, never secret values.
