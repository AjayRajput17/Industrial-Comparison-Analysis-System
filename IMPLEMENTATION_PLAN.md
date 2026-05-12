# FCS Architecture Restructure & Extension - Implementation Plan

This document tracks the step-by-step phases to restructure the FCS engineering comparison application into a scalable modular architecture without breaking existing logic, as well as adding the Report Generation feature.

## 🔴 MOST CRITICAL REQUIREMENT
**DO NOT CHANGE THE EXISTING COMPARISON SYSTEM LOGIC.** Outputs must remain functionally identical.

---

## 🏈 PHASE 1 — Restructure Existing Comparison System & Auth
**Goal:** Modularize without altering business logic or breaking existing authentication.
- [x] **Phase 1.1 — Create Folder Structure:** Create `config/`, `ui/`, `comparison_engine/`, `report_generator/`, `preprocessing/`, `exports/`, `auth/`, `utils/`, and `tests/`. Check app continuously.
- [x] **Phase 1.2 — Move Existing Comparison Logic:** Map `modules/comparator.py` and `modules/comment_engine.py` logic to `comparison_engine/` exactly as-is. Verify matching output.
- [x] **Phase 1.3 — Move Existing Auth Logic:** Move the already implemented authentication system into the `auth/` module or appropriate UI routing.
- [x] **Phase 1.4 — Move UI Logic:** Shift Streamlit comparison UI from `app.py` directly into `ui/comparison_ui.py`. Make `app.py` a routing shell.
- [x] **Phase 1.5 — Move Utilities & Preprocessing:** Relocate column utilities to `preprocessing/` and file handlers to `utils/`.
- [x] **Phase 1.6 — Validate System:** CRITICAL. Confirm login works, and all comparison tabs, rows, modified counts, comments, and reports match legacy behavior exactly.

---

## 🚀 PHASE 2 — Report Generation Module
**Goal:** MBOM/EBOM standardization pipeline. Must remain strictly independent from the Comparison Engine.
- [x] **Phase 2.1 — Report Generation UI:** Create `ui/report_generation_ui.py` with standalone navigation via Sidebar.
- [x] **Phase 2.2 — MBOM/EBOM File Input:** Accept and validate Excel/CSV.
- [x] **Phase 2.3 — Structure Analyzer:** Implement dynamic top-row searching to correctly `detect_header_row()` and `validate_required_columns()`.
- [x] **Phase 2.4 — Schema Mapping:** Create config dictionaries to translate raw EBOM columns into the strict format expected by the comparison engine.
- [x] **Phase 2.5 — Report Builder:** Process raw data and construct standardized dataframes.
- [x] **Phase 2.6 — Report Export:** Route results through `exports/excel_exporter.py` for download.
- [x] **Phase 2.7 — Final Validation:** Download a generated report and upload it directly into the Comparison Engine to prove 100% interoperability.
