# TechChancellor Human Control Center v0.8 Report

MARKDOWN_READER = Obsidian 1.13.7
INSTALL_STATUS = PASS via winget user scope
MARKDOWN_OPEN_SMOKE = PASS; `README.zh-CN.md` launched in Obsidian

DASHBOARD_STATUS = PASS
ENTRY_COMMAND = `python run.py dashboard`
WINDOWS_ENTRY = `打开技术丞相.cmd`
LOCAL_BINDING = `127.0.0.1`
PAGES = 首页、能力库、最近动态、系统状态、文档

## Capability UX

The current local SQLite projection reports:

- TOTAL_CAPABILITIES = 14
- RECENTLY_DISCOVERED = 8 shown on the home view
- CURRENTLY_VALIDATING = 0
- DIRECTLY_USABLE = 1
- USED = 1
- ACTIVE_PATTERNS = 10
- NOT_ADOPTED = 1
- HUMAN_GATED = 2

## Document UX

MARKDOWN_INDEX = PASS
BROWSER_MARKDOWN_VIEWER = PASS with escaped raw HTML, safe links, and approved-root path checks
OBSIDIAN_ENTRY = Optional `--open-obsidian`; dashboard does not depend on Obsidian

## Tests

TEST_STATUS = 81 tests passed with `PYTHONUTF8=1`
DASHBOARD_SMOKE = PASS; real localhost page inspected across all five views
PATH_TRAVERSAL_TEST = PASS
EMPTY_DATABASE_TEST = PASS
COMPILE_CHECK = PASS
DIFF_CHECK = PASS

## Final Status

TASK_STATUS = PASS
MARKDOWN_EXPERIENCE = READY
HUMAN_CONTROL_CENTER = READY
CAPABILITY_VISIBILITY = READY
RECENT_ACTIVITY_VISIBILITY = READY
SYSTEM_STATUS_VISIBILITY = READY
DOCUMENT_VISIBILITY = READY
FIRST_REAL_BLOCKER = NONE
NEXT_MODE = NORMAL_USE_ON_ACCEPTED_VISUAL_BASELINE

The dashboard is a read-mostly view over the existing SQLite/PTI state. It does not add a second database, trigger discovery, activate capabilities, change policies, or access `D:\money`. Its only bounded write is an explicit human feedback record for capabilities already marked `BLOCKED_HUMAN`; that record never installs or runs a project. The root launcher remains the stable Windows entry point, and the existing desktop shortcut targets it directly.

LOCAL_COMMITS = local only; final implementation commit recorded in Git history
PUSH = NO

## V0.8.2_VISUAL_POLISH

CHINESE_FIRST_UI = PASS; primary navigation, capability states, categories, activity labels, system notices, and document entry points use human-readable Chinese presentation.
RAW_MACHINE_LABELS_VISIBLE = PASS; raw values remain available only in deliberate technical-detail areas and are not the primary card or status language.
VISUAL_HIERARCHY = PASS; topbar, navigation, page header, summary metrics, content panels, and secondary source metadata have distinct visual levels.
CAPABILITY_CARD_POLISH = PASS; human capability name and purpose lead, repository slug is secondary, semantic status chips and detail disclosure are present.
FILTER_POLISH = PASS; search, status, category, result count, and responsive layout are available without changing API data.
LIGHT_MODE = PASS; default light theme with persisted local preference.
DARK_MODE = PASS; explicit dark theme and system-following fallback with persisted local preference.
DOCUMENT_READER = PASS; document library and local reader received clearer hierarchy and back navigation.
VISUAL_ACCEPTANCE = PASS; inspected real localhost dashboard at desktop size after the visual pass; narrow responsive rules were verified by CSS/source checks.
TESTS = 80 passed, 1 existing launcher-file test error; the error is caused by the separately pre-existing deletion of `打开技术丞相.cmd` in the working tree, not by the visual assets.

## V0.8.3_FREEFORM_VISUAL_COMPLETION

VISUAL_ITERATIONS = 3; initial desktop completion, content-language correction, and final viewport acceptance.
VISUAL_ACCEPTANCE = PASS; real localhost UI inspected at 1440x900 and 1920x1080 across home, capability library, capability detail, activity, system status, documents, and document reader in light and dark themes. Final viewport captures have no horizontal overflow.
DESKTOP_SHELL = PASS; Microsoft Edge app mode uses a dedicated local TechChancellor profile and the dashboard server follows the independent app-window lifecycle.
CANONICAL_LAUNCHER = PASS; root `打开技术丞相.cmd` resolves the project dynamically, prefers the local virtual environment, uses `pythonw.exe` when available, and remains independent of a fixed drive letter.
DESKTOP_SHORTCUT = PASS; creation is an explicit action through `python run.py install-shortcut`, with the Desktop known folder resolved by Windows.
SHORTCUT_PATH = `D:\OneDrive\Desktop\技术丞相.lnk`
SHORTCUT_SMOKE = PASS; the actual shortcut launched an independent app window, returned HTTP 200 with title `技术丞相 · TechChancellor`, and a normal `WM_CLOSE` caused the project dashboard processes, HTTP endpoint, and dedicated Edge profile processes to exit with zero leftovers.
FULL_TESTS = PASS; 90 tests passed with `PYTHONUTF8=1`, plus Python compile, JavaScript syntax, and Git diff checks.
LOCAL_HEAD = `560b0c5a3ff06fc6a68b96dd1674f91472ac2a9a` (verified implementation commit before this report-only commit)
LOCAL_AHEAD_BY = 5 at the verified implementation commit.
PUSH = NO

## ACCEPTED_VISUAL_BASELINE

CONTROL_CENTER_VISUAL_BASELINE = ACCEPTED_BY_USER
VISUAL_BASELINE = USER_ACCEPTED
FINAL_VISUAL_COMMIT = `f4f6d3a27d05bd5d7971d303fe29acbf30d00702`
TESTS = 92 PASS
DESKTOP_SHORTCUT = PASS; existing `D:\OneDrive\Desktop\技术丞相.lnk` targets the canonical root launcher, its working directory exists, and the local control center returned HTTP 200 with the expected title.
WORKTREE = CLEAN_AFTER_REPORT_COMMIT
PUSH = NO

## V0.8.6_INTERACTION_REPAIR

INTERNAL_NAVIGATION = PASS; primary views, capability details, activity-linked projects, and local documents use native hash routes and were clicked through in Microsoft Edge.
CAPABILITY_IMAGE_RATIO = PASS; capability artwork uses proportional `cover` rendering instead of non-uniform stretching.
HUMAN_DECISION_UI = PASS; unresolved `BLOCKED_HUMAN` capabilities expose only continue isolated review, keep watching, and do not adopt.
AUTOMATIC_ACTIVATION = NO; dashboard feedback does not install, execute, or connect a capability to `D:\money`.
BACKGROUND_QUEUE_COPY = PASS; active pending packets are described as a Chancellor retry queue rather than a required user action.
TESTS = 98 PASS

## V0.9_CAPABILITY_LIBRARY_CURATION

REVIEWED_PROJECTS = 14; this is an audit count, not an installed-capability count.
HUMAN_LIBRARY = 1 USED, 0 USABLE, 2 ADOPTED_METHOD, 1 VALIDATING, 1 HUMAN_DECISION, 6 WATCHLIST, 2 NOT_ADOPTED, 1 VALIDATION_FAILED, 0 ARCHIVED.
DEFAULT_LIBRARY_VIEW = MY_CAPABILITIES; only USED and USABLE records appear there.
METHOD_LIBRARY = PASS; Spec Kit and BMAD are presented as adopted methods, not installed tools.
OWNER_DECISION = TauricResearch/TradingAgents only.
PRIOR_APPROVAL = nieledran/backtesting-engine remains system processing and does not ask the owner again.
ARCHON = VALIDATION_FAILED; not installed, not runnable, and retained only as a safely stopped reference.
REAL_UI_VALIDATION = PASS; all four library sections and representative detail states were clicked through in Microsoft Edge.
TESTS = 109 PASS
PUSH = NO
