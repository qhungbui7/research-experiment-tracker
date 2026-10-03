# Changelog


## 2026-10-03

- 19:35 - Overhauled Lineage Graph UI/UX: removed unwanted wheel/trackpad scroll-zoom, replacing it with smooth 2D canvas panning and reserving zoom exclusively for Ctrl/Cmd+wheel, trackpad pinch, and dedicated toolbar buttons
- 19:35 - Implemented 4 smart Lineage Graph layout engines: Timeline Flow (chronological spine with vertically clustered findings eliminating spaghetti links), Clustered DAG (research epochs), Focus Subgraph (isolated 1-hop causal neighborhood), and All (compact multi-column)
- 19:35 - Added live in-graph search filtering with dimming and Enter-to-center navigation, type filtering pills (All, Rounds, Issues, P0/P1 Blockers), and dynamic bounding-box screen fitting
- 19:35 - Added defensive null-safe element access across all dashboard views to ensure rock-solid rendering across any data subset
- 17:58 - Fixed client-side TypeError in initRunComparer by safely resolving round/round_name and focus/subject properties
- 17:58 - Added defensive try-catch wrappers around all view initializers and registered window.showTab/switchTab
- 17:42 - Added Section 8 to PRINCIPLES.md adopting autonomous research principles (tree-search, dual-agent verification, anti-narrative rules, confound isolation)
- 17:42 - Implemented interactive Progressive Hypothesis Tree Search Visualizer & Decision Matrix in Directions tab
- 17:42 - Integrated Autonomous Discovery & Rigor Scorecard in Overview tab with claim provenance and early-pruning metrics
- 13:50 - Migrate and generalize experiment tracking, review lineage, and methodology framework into standalone package
- 13:50 - Add PRINCIPLES.md defining pre-registered decision protocols, provenance standards, and P0-P4 severity taxonomy
- 13:50 - Implement unified CLI (init, validate, build, snapshot, finalize, serve, status) with zero external dependencies
- 13:50 - Add comprehensive 19-test unit test suite and working demo project
- 14:15 - Add root-path auto-redirect in serve handler and deploy persistent systemd service on VPS for amt project
- 16:45 - Major UI/UX overhaul: multi-view dashboard (Executive KPIs, Issue Table, Decluttered Lineage Graph, Document Reader) with dark/light themes and resolution of all 'undefined' values
- 17:10 - Add interactive Research Directions view (hypotheses, stopping rules, path outcomes), Code & Fixes inspector, and inline markdown rendering engine (bold, italics, code, math, links, formatted tables)
- 17:35 - Integrate KaTeX & offline Unicode math engine, fix ASCII box diagrams, add W&B-style Run Comparer, dynamic document Table of Contents, and Cmd+K command palette
