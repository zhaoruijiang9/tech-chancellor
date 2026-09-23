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
NEXT_MODE = NORMAL_USE_AND_ITERATIVE_UX_IMPROVEMENT

The dashboard is a read-only view over the existing SQLite/PTI state. It does not add a second database, trigger discovery, activate capabilities, change policies, or access `D:\money`. No desktop shortcut was created; the root launcher is the stable Windows entry point.

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
