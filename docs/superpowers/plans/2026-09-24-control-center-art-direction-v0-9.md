# TechChancellor Control Center Art Direction V0.9

**Goal:** Turn the existing functional dashboard into an art-directed desktop experience while preserving every read-only API and lifecycle meaning.

**Approved direction:** A warm, mature female technical adviser anchors a quiet studio scene. Real HTML glass surfaces present one primary intelligence item and a five-card capability gallery. Edges stay pale and low contrast; decorative particles and fragmented metrics are intentionally absent.

## Boundaries

- Keep the Python localhost server, SQLite read model, five views, Chinese-first labels, and read-only behavior.
- Do not access or modify `D:\money`.
- Generated images are presentation assets only. Text, controls, statuses, filtering, navigation, and data remain accessible HTML.
- Keep light, dark, reduced-motion, keyboard, and responsive behavior.
- Bind only to `127.0.0.1`; do not add remote runtime assets or a frontend framework.

## Implementation

- Add a clean adviser scene and a five-panel capability artwork atlas under `dashboard_assets`.
- Serve approved image assets from the existing local HTTP server with fixed MIME types.
- Replace the heavy left rail with a compact glass top bar and give the content a full-width canvas.
- Rebuild the home view around one featured discovery and one capability gallery.
- Carry the same material, typography, spacing, and artwork language into library, detail, activity, system, and document views.
- Add restrained page entrance, hover, focus, and glass-depth transitions; disable them for reduced motion.

## Acceptance

- Asset and server tests pass; images load from localhost without network access.
- Existing dashboard semantic tests and the full unit suite remain green.
- Desktop and mobile screenshots show no blank images, overlap, clipped controls, or unreadable text.
- Dark mode remains usable and the app still works with images unavailable.
