# Optional Secure Execution Backend V0.1

This post-v0.2.0 development feature is optional. Initialization, discovery,
read-only capability adapters and the dashboard still work without Docker.
Installing Docker is not permission to execute arbitrary repositories.

## Supported Host

Windows Home can use Microsoft WSL2 and Docker Desktop's per-user installation
with the WSL2 backend and Linux containers. No independent Ubuntu distribution,
Windows containers, Kubernetes, paid Enhanced Container Isolation, account login
or security-policy changes are required by this adapter.

Use the official [WSL installation instructions](https://learn.microsoft.com/en-us/windows/wsl/install)
and [Docker Desktop Windows instructions](https://docs.docker.com/desktop/setup/install/windows-install/).
Review Docker's applicable licensing terms for your own use. TechChancellor does
not install or accept licensing terms on another user's behalf.

## Qualification Is Local State

The backend starts UNCONFIGURED on every clean installation. A trusted operator
must run real hostile containment tests on that machine before enabling it.
Evidence must cover non-root execution, read-only source/input/root, allowed
output, minimal environment, inaccessible synthetic host secrets and credentials,
absent Docker socket/host drives, dropped capabilities, no-new-privileges,
PID isolation, failed DNS/HTTP/TCP attempts, timeout cleanup, removed child
processes, unchanged host service/scheduler/PATH inventory, and removed fixtures.
Use fake secrets only, not real credentials or protected-project contents.

`state/containment-evidence.json` is a machine-local qualification receipt,
not a shipped default and not a portable certificate. Its exact SHA-256,
the full local Docker executable path and the tested image digest belong in
ignored `state/secure_execution.local.json`. Do not copy another machine's
receipt or create a PASS from a unit-test mock. V0.1 permits only the image
actually covered by the receipt; a new image requires fresh qualification.
The local named-pipe endpoint cannot be overridden to a remote daemon.

The receipt must also match the live Linux/WSL2 kernel and Docker server version.
Health is checked at execution and promotion. Dashboard reads show receipt
status without starting Docker; they do not claim the engine is currently up.
Configuration and receipt changes never automatically register a capability.
Explicit `register_verified_backend(root, db)` validates the receipt and live
engine before recording VERIFIED and AVAILABLE. USED needs an actual pilot,
not synthetic tests. Runtime JSON, paths and SQLite remain ignored local state.

## Existing Activation Pipeline

Execution uses the existing queue, pinned archive acquisition, quarantine,
static-review, install/test/evaluation phases, active pointer and rollback.
No second activation engine or persistent candidate service is created.

A trusted, reviewed plan is required at
`state/secure_execution/plans/repo-<repository_id>.json`. It declares:

- `execution`: backend `DOCKER_WSL2_LINUX`, digest-pinned image, exact 40-character
  source pin, runtime type, argument-list command, flat expected output names,
  fixed `/candidate` working directory, `NONE` network policy and resource bounds.
- `target_capability`: V0.1's implemented evaluator supports `CONTEXT_COMPRESSION`.
- `evaluation`: `BOUNDED_TEXT_COMPRESSION`, synthetic `input_text`, literal
  `required_facts`, and `minimum_reduction` between 0.1 and 0.9.

Plans are not generated from upstream README instructions. The candidate still
needs a reviewed source decision and a matching capability mapping. Existing
failures, sensitive financial projects and human gates are not overridden.
Source and plan changes after review stop the job.

V0.1 accepts bounded UTF-8 source archives, rejects links, Windows aliases,
opaque binaries, oversized files and hazardous static findings. It does not
perform networked dependency builds, pip/npm installations, MCP/server
deployment or desktop capture. The selected tested image must already contain
the command's runtime. Declaring `PYTHON` does not install Python into an image.

## Execution Boundary

Each candidate runs as UID/GID 65534 in an ephemeral Linux container with:

- network NONE; read-only root; ALL capabilities dropped; no-new-privileges;
- private IPC, bounded CPU/memory/PIDs and 1-120 second candidate timeout;
- exactly two host mounts: per-job source and synthetic input, both read-only;
- 16 MiB temporary `/tmp` and 16 MiB `/output` tmpfs, with no writable host mount;
- a minimal candidate environment, no host home/profile/credential inheritance;
- no socket, named-pipe, device, host PID/network or drive mounts.

Only allowlisted regular UTF-8 output files up to 64 KiB each are accepted.
Tar entries are parsed in memory, never extracted to the host. Candidate
stdout/stderr remain in bounded tmpfs. Outputs may be produced concurrently by
candidate processes; collection is bounded and rejects links, not an atomic
snapshot or a guarantee of semantic correctness. Containers are destroyed in
success and failure paths. A finite PID-1 lifetime limits orphan lifetime after
a controller crash; normal teardown verifies actual daemon-reported absence.

Functional success and cleanup are necessary, not sufficient for promotion.
The initial evaluator compares UTF-8 byte count with a no-compression baseline
while requiring declared literal facts. It is a single synthetic-task measure,
not proof of general semantic compression quality. No meaningful improvement
means no AVAILABLE promotion. Synthetic tests never constitute real use.

## Limits

Docker Desktop/WSL2 containers are not a guarantee against Linux kernel,
hypervisor, WSL2 or Docker vulnerabilities. Qualification only establishes the
specific tested controls on the recorded host/image versions. This backend
does not authorize protected-project access, credentials, privileged actions,
persistent services, financial accounts or automatic trading.

Generic tests: `python -m unittest discover -s tests -v`. Unit-test Docker mocks
are not host-containment evidence. Keep real host and fresh-DB integration
receipts separate from the unit-test result.
