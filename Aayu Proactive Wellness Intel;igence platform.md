# AAYU: Proactive Wellness Intelligence Platform
## Complete Project Documentation v1.0

**Project**: AAYU — Proactive Wellness Intelligence  
**Database**: `WELLNESS_AI` on Snowflake  
**Account**: vt58024 (GCP me-central2)  
**Author**: ARNAB74  
**Date**: October 2026  
**Status**: Research Prototype — All classifications PROVISIONAL

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Sources & Research Population](#3-data-sources--research-population)
4. [Pipeline: RAW_DATA Layer](#4-pipeline-raw_data-layer)
5. [Pipeline: IDENTITY Layer](#5-pipeline-identity-layer)
6. [Pipeline: CURATED Layer](#6-pipeline-curated-layer)
7. [Pipeline: FEATURES Layer](#7-pipeline-features-layer)
8. [Pipeline: METRICS Layer](#8-pipeline-metrics-layer)
9. [Pipeline: SEMANTIC Layer](#9-pipeline-semantic-layer)
10. [Snowflake Semantic Views](#10-snowflake-semantic-views)
11. [Cortex Agent: Research Agent](#11-cortex-agent-research-agent)
12. [Synthetic Demo Data](#12-synthetic-demo-data)
13. [Public Demo Agent & Streamlit App](#13-public-demo-agent--streamlit-app)
14. [Pipeline Audit & Fixes](#14-pipeline-audit--fixes)
15. [Design Decisions & Trade-offs](#15-design-decisions--trade-offs)
16. [Known Limitations](#16-known-limitations)
17. [Future Roadmap](#17-future-roadmap)
18. [Appendix: Object Inventory](#18-appendix-object-inventory)
19. [Appendix: Row Counts Across Pipeline](#19-appendix-row-counts-across-pipeline)
20. [Appendix: Related Documents](#20-appendix-related-documents)

---

## 1. Project Vision

AAYU is a **proactive wellness intelligence platform** that transforms raw wearable sensor data, self-reported wellness scores, and clinical metabolic measurements into actionable health insights delivered through a conversational AI agent.

The core idea: instead of dashboards that require users to interpret numbers, AAYU provides **personal context** — "Your sleep debt is worsening compared to your own 28-day baseline" rather than "You slept 6.2 hours."

### What AAYU Does

1. **Ingests** data from 5 research datasets (Fitbit, Garmin, PMData, Depresjon, Shanghai CGM)
2. **Normalizes** across device-specific formats into unified health views
3. **Computes** personal baselines, z-scores, trends, and composite health states
4. **Exposes** a semantic contract that a conversational AI agent can query
5. **Answers** natural language questions like "How is sleep for person 198?" with contextualized, caveated responses

### What AAYU Is Not

- Not a clinical system — all classifications are PROVISIONAL engineering prototypes
- Not real-time — processes historical research data, not live sensor feeds
- Not personalized medicine — does not diagnose, prescribe, or recommend treatment
- All 225 subjects are from public research datasets, not actual AAYU users

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CONVERSATIONAL LAYER                       │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │ AAYU_RESEARCH_AGENT │  │ AAYU_PUBLIC_AGENT (demo)     │  │
│  │ 3 tools, 225 subj.  │  │ 2 tools, 12 synthetic subj. │  │
│  └────────┬────────────┘  └────────────┬─────────────────┘  │
├───────────┼────────────────────────────┼────────────────────┤
│           │     SEMANTIC LAYER         │                     │
│  ┌────────▼────────────┐  ┌───────────▼──────────────┐      │
│  │ AAYU_WELLNESS       │  │ AAYU_DEMO_WELLNESS       │      │
│  │ AAYU_DATA_QUALITY   │  │ AAYU_DEMO_METABOLIC      │      │
│  │ AAYU_METABOLIC      │  │ (filtered: ID >= 9001)   │      │
│  └────────┬────────────┘  └──────────────────────────┘      │
├───────────┼─────────────────────────────────────────────────┤
│           │     COMPUTE VIEWS (SEMANTIC schema)              │
│  SUBJECT_HEALTH_CONTEXT ─── SUBJECT_DOMAIN_DETAIL            │
│  SUBJECT_DATA_QUALITY ───── SUBJECT_METABOLIC_CONTEXT        │
├──────────────────────────────────────────────────────────────┤
│           METRICS LAYER                                      │
│  PERSONAL_BASELINES ── AAYU_HEALTH_STATE ── HEART_RATE_TRENDS│
│  SLEEP_DEBT_TRACKER ── METABOLIC_RISK_PIT ── DATA_QUALITY    │
├──────────────────────────────────────────────────────────────┤
│           FEATURES LAYER                                     │
│  SLEEP_FEATURES ── ACTIVITY_FEATURES ── HEART_RATE_FEATURES  │
│  WELLNESS_FEATURES ── CIRCADIAN_FEATURES ── METABOLIC_FEAT.  │
├──────────────────────────────────────────────────────────────┤
│           CURATED LAYER                                      │
│  DAILY_HEALTH_SUMMARY ── SLEEP_SESSIONS ── HEART_RATE_HOURLY │
│  WELLNESS_SELF_REPORTS ── METABOLIC_VISITS ── USER_PROFILE_V2│
├──────────────────────────────────────────────────────────────┤
│           IDENTITY LAYER                                     │
│  PERSON_REGISTRY ── PERSON_SOURCE_IDENTITY                   │
│  PERSON_IDENTITY_LOOKUP (denormalized join view)             │
├──────────────────────────────────────────────────────────────┤
│           RAW_DATA LAYER (22 tables, ~34.4M rows)            │
│  Fitbit (7 tables) ── Garmin (1) ── PMData (8)              │
│  Depresjon (2) ── CGM (3) ── CGM_PATIENT (1)                │
└──────────────────────────────────────────────────────────────┘
```

Every layer is built from **SQL views** (no materialized tables after RAW_DATA), meaning the entire pipeline recomputes on query. This ensures consistency but means query performance depends on warehouse size.

---

## 3. Data Sources & Research Population

### Five Public Research Datasets

| Dataset | Subjects | Source Country | Time Period | Primary Data |
|---------|----------|---------------|-------------|--------------|
| **Fitbit (Fitabase MTurk)** | 35 | US | 2016 | Heart rate (5-sec), sleep, daily activity, weight |
| **Garmin Vivosmart** | 7 | Unknown | 2019 | Epoch-level HR, sleep stages, activity, stress |
| **PMData** | 16 | Norway | 2019-2020 | Heart rate, sleep stages, self-reports (mood, fatigue, stress, readiness), exercise |
| **Depresjon** | 55 | Norway | 2002-2006 | Minute-level actigraphy, depression scores (MADRS) |
| **Shanghai CGM** | 112 | China | 2020-2021 | CGM glucose, metabolic labs (HbA1c, lipids, renal), visit-level clinical data |

**Total: 225 unique research subjects, ~34.4 million raw rows**

### Cohort Boundaries

There is **zero overlap** between the wellness and metabolic cohorts:
- **Wellness cohort** (113 subjects): Fitbit + Garmin + PMData + Depresjon — wearable sensor and self-report data
- **Metabolic cohort** (112 subjects): CGM patients — clinical visit data with lab results

This is a fundamental data characteristic, not a design choice. The research datasets come from completely different studies with different populations.

---

## 4. Pipeline: RAW_DATA Layer

**Schema**: `WELLNESS_AI.RAW_DATA`  
**Objects**: 22 tables  
**Total rows**: ~34.4 million

The RAW_DATA layer contains source data exactly as loaded, with no transformations. Each table maps to a specific dataset file.

### Key Tables

| Table | Rows | Grain | Key Columns |
|-------|------|-------|-------------|
| FITBIT_HEARTRATE | 3,638,339 | 5-second | USER_ID, RECORDED_AT, HEART_RATE_BPM |
| FITBIT_DAILY_ACTIVITY | 1,397 | Daily | USER_ID, ACTIVITY_DATE, TOTAL_STEPS, CALORIES |
| FITBIT_SLEEP_DAY | 413 | Daily | USER_ID, SLEEP_DAY, TOTAL_MINUTES_ASLEEP |
| GARMIN_VIVOSMART | 8,167,178 | Per-minute epoch | PARTICIPANT_ID, RECORD_DATE, RECORD_TIME, SLEEP_LEVEL, ACTIVITY_TYPE |
| PMDATA_HEART_RATE | 20,991,392 | Sub-second | PARTICIPANT_ID, RECORDED_AT, HEART_RATE_BPM |
| PMDATA_WELLNESS | 1,747 | Daily | PARTICIPANT_ID, FATIGUE, MOOD, READINESS, STRESS |
| PMDATA_SLEEP | 2,064 | Per-session | PARTICIPANT_ID, DEEP/LIGHT/REM/WAKE_MINUTES |
| DEPRESJON_ACTIGRAPHY | 1,571,706 | Per-minute | PARTICIPANT_ID, RECORDED_AT, ACTIVITY |
| CGM_PATIENT | 112 | Per-patient | BASE_PATIENT_ID, DIABETES_TYPE, latest lab values |
| CGM_PATIENT_VISIT | 125 | Per-visit | BASE_PATIENT_ID, VISIT_DATE, HBA1C, BMI, eGFR |

### ID Format Differences

Each dataset uses a different ID format:
- Fitbit: large integers (e.g., `1503960366`)
- PMData: text codes (e.g., `p01`)
- Garmin: single letters (e.g., `A`)
- Depresjon: condition/control labels (e.g., `condition_12`)
- CGM: numeric strings (e.g., `1001`)

This is resolved in the IDENTITY layer.

---

## 5. Pipeline: IDENTITY Layer

**Schema**: `WELLNESS_AI.IDENTITY`  
**Objects**: 2 tables + 1 view  
**Purpose**: Assign a stable `PERSON_ID` to every research subject across all source systems

### Design

| Object | Type | Purpose |
|--------|------|---------|
| PERSON_REGISTRY | Table | One row per person. Assigns PERSON_ID, stores demographics, observation span |
| PERSON_SOURCE_IDENTITY | Table | One row per source linkage. Maps PERSON_ID ↔ SOURCE_SYSTEM + SOURCE_SUBJECT_ID |
| PERSON_IDENTITY_LOOKUP | View | Denormalized join of both tables. Exposes `LEGACY_UNIVERSAL_USER_ID` as `SOURCE_PERSON_KEY` for backward compatibility |

### The UNIVERSAL_USER_ID Bridge

The CURATED views construct a synthetic key: `'fitbit_' || USER_ID`, `'pmdata_' || PARTICIPANT_ID`, etc. The IDENTITY layer stores the same key as `LEGACY_UNIVERSAL_USER_ID` (e.g., `fitbit_1503960366`). This allows downstream joins via `USER_PROFILE_V2.UNIVERSAL_USER_ID`.

All 225 subjects have `PERSON_TYPE = 'RESEARCH_SUBJECT'` and `IDENTITY_CONFIDENCE = 'UNLINKED'` (no cross-dataset linking attempted).

---

## 6. Pipeline: CURATED Layer

**Schema**: `WELLNESS_AI.CURATED`  
**Objects**: 7 views  
**Purpose**: Normalize heterogeneous source formats into unified, deduplicated views

### Views

| View | Rows | Sources | Key Logic |
|------|------|---------|-----------|
| DAILY_HEALTH_SUMMARY | 5,466 | Fitbit activity, Depresjon actigraphy | QUALIFY ROW_NUMBER() dedup on Fitbit; activity from actigraphy for Depresjon |
| SLEEP_SESSIONS | 3,177 | Fitbit sleep, Garmin sleep, PMData sleep | Garmin: UPPER() for case-sensitivity, COUNT(DISTINCT RECORD_TIME) for 12-sec epochs, WHERE ADJUSTED_ACTIVITY_TYPE='SLEEPING' |
| HEART_RATE_HOURLY | 75,859 | Fitbit HR, PMData HR, Garmin HR | Hourly AVG/MIN/MAX/STDDEV aggregation |
| WELLNESS_SELF_REPORTS | ~1,747 | PMData wellness, Depresjon scores | Mood, fatigue, stress, readiness, depression scores |
| METABOLIC_VISITS | 141 | CGM_PATIENT_VISIT + CGM_PATIENT | CHRONOLOGICAL_SEQ via ROW_NUMBER() to fix reversed VISIT_SEQ for 2 patients |
| METABOLIC_PROFILE | 112 | CGM_PATIENT | Latest-visit clinical snapshot |
| USER_PROFILE_V2 | ~237 | IDENTITY.PERSON_IDENTITY_LOOKUP | Exposes UNIVERSAL_USER_ID for all subjects |

### Notable Fixes Applied

1. **Garmin sleep was completely missing (0 rows)** — three compounding bugs: case-sensitivity (`light` vs `LIGHT`), sub-minute epoch overcounting, and non-sleep activity tagged with sleep levels
2. **Fitbit daily duplicates** — some USER_ID+DATE combinations had multiple rows; resolved with QUALIFY ROW_NUMBER()
3. **Metabolic VISIT_SEQ reversed** — patients 2017 and 2055 had VISIT_SEQ not matching chronological VISIT_DATE; added CHRONOLOGICAL_SEQ

---

## 7. Pipeline: FEATURES Layer

**Schema**: `WELLNESS_AI.FEATURES`  
**Objects**: 6 views  
**Purpose**: Compute windowed statistics, rolling averages, and standardized features from curated data

### Views

| View | Rows | Key Features |
|------|------|-------------|
| SLEEP_FEATURES | 3,177 | 7-day/14-day/28-day rolling sleep duration, efficiency, deep/REM %, sleep debt (cumulative shortfall vs 8-hour target), quality flags |
| ACTIVITY_FEATURES | 4,212 | 7-day/28-day rolling steps, active minutes, trend detection |
| HEART_RATE_FEATURES | 3,090 | Resting HR (overnight min), 14-day z-scores for recovery detection, 28-day rolling average for baselines |
| WELLNESS_FEATURES | ~1,747 | Rolling mood, fatigue, stress averages |
| CIRCADIAN_FEATURES | ~1,747 | Sleep onset/offset variability (PMData only — requires timestamps) |
| METABOLIC_FEATURES | 141 | Visit-level HbA1c, BMI, eGFR, component scores, data quality flags |

### Dual Z-Score Design (Intentional)

The 14-day z-score (RESTING_HR_ZSCORE_14D) is used for **recovery anomaly detection** — a shorter window is more sensitive to recent changes. The 28-day rolling average is used for **personal baselines** — a longer window provides a more stable norm. This is intentional, not a bug.

---

## 8. Pipeline: METRICS Layer

**Schema**: `WELLNESS_AI.METRICS`  
**Objects**: 10 views  
**Purpose**: Derive health states, composite scores, and coaching-ready classifications

### Key Metrics

| View | Purpose |
|------|---------|
| PERSONAL_BASELINES | 28-day rolling descriptive statistics per subject per domain. Baseline is only computed when 10+ observations exist (SUFFICIENT confidence) |
| AAYU_HEALTH_STATE | Daily composite: sleep state, circadian state, recovery state, activity state, data quality classification. All PROVISIONAL |
| HEART_RATE_TRENDS | Recovery classification from resting HR z-scores. GOOD_RECOVERY (z < -1.0), NORMAL (-1.0 to +1.0), ELEVATED (z > +1.0) |
| SLEEP_DEBT_TRACKER | 7-day cumulative sleep shortfall vs 8-hour target |
| METABOLIC_RISK_PIT | Point-in-time metabolic risk score (0-100) from HbA1c + BMI + eGFR, equally weighted. Missing components score NULL (not 0, to avoid optimistic bias) |
| DATA_QUALITY_REPORT | Coverage and quality per subject per domain across 5 domains (SLEEP, HEART_RATE, ACTIVITY, WELLNESS, METABOLIC) |

### IS_LATEST_VISIT Removal

The original metabolic pipeline included an `IS_LATEST_VISIT` flag. This was identified as a **temporal leakage** risk — the existence of a "latest" flag on earlier visits reveals that a future visit occurred. It was:
- Demoted to `_METADATA_IS_LATEST_VISIT` in METRICS
- Completely removed from SEMANTIC views
- Replaced with query-time `ORDER BY VISIT_DATE DESC LIMIT 1`
- Regression tests T19/T20 added to prevent reintroduction

---

## 9. Pipeline: SEMANTIC Layer

**Schema**: `WELLNESS_AI.SEMANTIC`  
**Objects**: 4 compute views + 3 Snowflake Semantic Views + 1 agent + 2 tables

The SEMANTIC layer provides a **stable application contract** that the Cortex Agent queries through. It decouples the conversational AI from the internal metrics implementation.

### Compute Views (regular SQL views)

| View | Rows | Purpose |
|------|------|---------|
| SUBJECT_HEALTH_CONTEXT | 4,478 | One row per subject per day. Holistic snapshot: sleep state, circadian state, recovery state, activity state, domains available, data quality |
| SUBJECT_DOMAIN_DETAIL | 12,615 | One row per subject per domain per day. Current value, personal baseline, deviation, trend, confidence |
| SUBJECT_DATA_QUALITY | 304 | One row per subject per domain per source. Coverage %, observation count, quality state |
| SUBJECT_METABOLIC_CONTEXT | 141 | One row per subject per visit. HbA1c, BMI, eGFR, risk score, trend, completeness |

### Supporting Tables

| Table | Rows | Purpose |
|-------|------|---------|
| SEMANTIC_DEFINITIONS | 41 | Concept dictionary: field name → description, provenance, dependencies |
| AGENT_EVAL_DATASET | 25 | Evaluation test cases: INPUT_QUERY + GROUND_TRUTH for agent testing |

---

## 10. Snowflake Semantic Views

Snowflake Semantic Views are **native schema objects** (not regular views) that define business concepts over data for Cortex Analyst consumption. They specify tables, dimensions, facts, metrics, relationships, verified queries, and custom instructions in a structured format.

### Three Production Semantic Views

| Semantic View | Base Tables | Verified Queries | Custom Instructions |
|--------------|-------------|-----------------|-------------------|
| AAYU_WELLNESS | SUBJECT_HEALTH_CONTEXT, SUBJECT_DOMAIN_DETAIL | 11 | sql_generation + question_categorization |
| AAYU_DATA_QUALITY | SUBJECT_DATA_QUALITY | 5 | sql_generation + question_categorization |
| AAYU_METABOLIC | SUBJECT_METABOLIC_CONTEXT | 6 | sql_generation + question_categorization |

### Key Syntax Learnings

1. **Clause ordering**: `TABLES → RELATIONSHIPS → FACTS → DIMENSIONS → METRICS` (Snowflake enforces this)
2. **COMMENT positioning**: Must precede SAMPLE_VALUES and IS_ENUM in dimension definitions
3. **Verified queries**: Cannot be added via `ALTER SEMANTIC VIEW`; must use the YAML approach: `SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW()` → modify YAML → `CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML()`
4. **Custom instructions**: Added via `module_custom_instructions` block in YAML (not supported in DDL)
5. **SAMPLE_VALUES must match real data**: Using values that don't exist in the data causes validation failures

---

## 11. Cortex Agent: Research Agent

**Object**: `WELLNESS_AI.SEMANTIC.AAYU_RESEARCH_AGENT`  
**Display Name**: AAYU Research Intelligence  
**Access**: Snowsight UI (AI & ML > Agents) or REST API

### Configuration

```yaml
models:
  orchestration: auto
instructions:
  response: [Research-focused instructions with PROVISIONAL caveats]
  orchestration: [Tool routing rules]
tools:
  - Wellness (→ AAYU_WELLNESS semantic view)
  - DataQuality (→ AAYU_DATA_QUALITY semantic view)
  - Metabolic (→ AAYU_METABOLIC semantic view)
```

### What It Can Answer

- "How is sleep for person 198?" → Queries AAYU_WELLNESS
- "Do we have enough data for person 209?" → Queries AAYU_DATA_QUALITY
- "What is the metabolic trajectory for person 27?" → Queries AAYU_METABOLIC
- "How many subjects have critical sleep debt?" → Aggregate queries
- "Compare T1DM vs T2DM patients" → Cross-patient metabolic analysis

### What It Cannot Answer

- Real-time physiological state (all data is historical)
- Clinical advice, diagnosis, or treatment recommendations
- Questions about subjects outside the 225 research population
- Cross-cohort queries (e.g., sleep data for metabolic patients)

### Evaluation

25 test cases stored in `WELLNESS_AI.SEMANTIC.AGENT_EVAL_DATASET` covering:
- Correct tool routing (Wellness vs DataQuality vs Metabolic)
- Factual accuracy against known data
- PROVISIONAL caveat inclusion
- Appropriate decline for out-of-scope questions
- Handling of NULL/unavailable domains

---

## 12. Synthetic Demo Data

To enable a **public-facing demo** without exposing real research data, 12 synthetic subjects were created with varied health patterns.

### Wellness Cohort (PERSON_ID 9001-9005, 9011)

| ID | Label | Days | Sources | Health Pattern |
|----|-------|------|---------|---------------|
| 9001 | Active Athlete | 90 | Fitbit + PMData | High steps (~14K/day), good sleep (~7.5h), low resting HR (~52 bpm), occasional overtraining spikes |
| 9002 | Stressed Professional | 60 | Fitbit + PMData | Low activity (~6.5K steps), poor sleep (~5.5h), elevated HR (~78 bpm), high stress self-reports |
| 9003 | Garmin Runner | 45 | Garmin + PMData | Good overall, morning run pattern visible in HR, variable sleep stages |
| 9004 | Poor Sleeper | 30 | Fitbit only | Low sleep (~5h improving to ~6h), low efficiency (75%), no self-reports |
| 9005 | Balanced Baseline | 60 | Fitbit + PMData | Normal everything — the "control" profile for comparison |
| 9011 | Sparse Wellness | 5 | Fitbit only | Only 5 days of data — all baselines INSUFFICIENT, demonstrates data quality guardrails |

### Metabolic Cohort (PERSON_ID 9006-9010, 9012)

| ID | Label | Visits | Type | Health Pattern |
|----|-------|--------|------|---------------|
| 9006 | Well-Controlled T2DM | 3 | T2DM | HbA1c improving (51→48→44 mmol/mol), BMI decreasing, normal kidney function |
| 9007 | Worsening T1DM | 4 | T1DM | HbA1c worsening (54→58→63→66), young patient, escalating insulin regimen |
| 9008 | New Diagnosis | 2 | T2DM | First visit very high (HbA1c 76), second visit improved (63), obese BMI |
| 9009 | Stable Elderly | 3 | T2DM | HbA1c steady (~53), declining eGFR (58→56→53) — kidney concern |
| 9010 | Metabolic Syndrome | 3 | T2DM | Everything elevated — lipids, glucose, BMI >35, hypertension |
| 9012 | Sparse Metabolic | 1 | T2DM | Single visit, eGFR missing → DATA_COMPLETENESS=INCOMPLETE, demonstrates unreliable scoring |

### How Synthetic Data Flows

Synthetic data is inserted into the **same RAW_DATA tables** as real data, using PERSON_ID range 9001+. Because the entire pipeline is views, it flows automatically:

```
RAW_DATA (inserts) → CURATED (auto) → FEATURES (auto) → METRICS (auto) → SEMANTIC (auto)
```

The `DEMO_SEMANTIC` schema adds a `WHERE PERSON_ID >= 9001` filter to isolate synthetic subjects for the public demo, ensuring zero leakage of real research data.

---

## 13. Public Demo Agent & Streamlit App

### DEMO_SEMANTIC Schema

| Object | Type | Purpose |
|--------|------|---------|
| SUBJECT_HEALTH_CONTEXT | View | Filtered: PERSON_ID 9001-9011 |
| SUBJECT_DOMAIN_DETAIL | View | Filtered: PERSON_ID 9001-9011 |
| SUBJECT_METABOLIC_CONTEXT | View | Filtered: PERSON_ID 9006-9012 |
| SUBJECT_DATA_QUALITY | View | Filtered: PERSON_ID >= 9001 |
| AAYU_DEMO_WELLNESS | Semantic View | Points to filtered wellness views |
| AAYU_DEMO_METABOLIC | Semantic View | Points to filtered metabolic views |
| AAYU_DEMO_AGENT | Agent | Lighter demo agent |
| AAYU_PUBLIC_AGENT | Agent | Hardened public-facing agent (v1.0) |

### AAYU_PUBLIC_AGENT — Hardened System Prompt

The public agent has a comprehensive system prompt covering:

1. **Cohort Isolation** — strict mapping of PERSON_IDs to tools. Cross-cohort queries are declined with explanation, not errored
2. **Data Quality Guardrails** — 6 specific triggers (INSUFFICIENT baseline, INCOMPLETE metabolic, FIRST_VISIT, NULL eGFR, sparse subjects 9011/9012)
3. **Classification Disclaimer** — every answer ends with PROVISIONAL caveat
4. **Off-Topic Safety** — clinical advice, real people, data modification, system prompt probing, jailbreak attempts all handled
5. **Orchestration Instructions** — separate tool routing rules that prevent the wrong tool from being called
6. **Execution Environment** — each tool specifies `warehouse: COMPUTE_WH`

### Streamlit Application

**File**: `aayu_app.py` (deployed to Streamlit Community Cloud)  
**Auth**: Snowflake credentials via `st.secrets`  
**Agent Call**: `SNOWFLAKE.CORTEX.DATA_AGENT_RUN()` with JSON request body

Layout:
- **Sidebar**: Dynamic sample questions based on selected subject (15 wellness or 12 metabolic questions), general questions, cross-cohort test buttons
- **Main area**: Header, 12 subject buttons (2 rows: 6 wellness + 6 metabolic), chat history, prompt bar
- **Flow**: Select subject → click sample question (or type freely) → agent responds in chat

---

## 14. Pipeline Audit & Fixes

A comprehensive audit was performed across all pipeline layers, discovering and fixing 18 issues.

### Critical Fixes

| # | Issue | Layer | Impact | Fix |
|---|-------|-------|--------|-----|
| 1 | Garmin sleep completely missing (0 rows) | CURATED | 7 subjects had no sleep data | UPPER() for case-sensitivity, COUNT(DISTINCT RECORD_TIME) for epoch counting, WHERE ADJUSTED_ACTIVITY_TYPE='SLEEPING' |
| 2 | Fitbit daily duplicates | CURATED | Inflated row counts | QUALIFY ROW_NUMBER() dedup |
| 3 | VISIT_SEQ reversed for 2 patients | CURATED | Wrong visit ordering | Added CHRONOLOGICAL_SEQ via ROW_NUMBER() |
| 4 | IS_LATEST_VISIT temporal leakage | METRICS/SEMANTIC | Earlier visits reveal future existence | Demoted to _METADATA, removed from semantic layer, regression tests added |
| 5 | RESTING_HR z-score window mismatch | METRICS | Documentation said 28-day but was 14-day | Clarified as intentional: 14-day for recovery detection, 28-day for baselines |
| 6 | DATA_QUALITY_REPORT only 3 domains | METRICS | Missing WELLNESS and METABOLIC | Expanded to 5 domains |
| 7 | COVERAGE_PCT exceeded 100% | METRICS | Misleading quality metric | Capped at 100 |
| 8 | RECOVERY_STATE had 4 tiers in docs but 3 in data | SEMANTIC | MILDLY_ELEVATED never existed | Corrected to 3-tier: GOOD_RECOVERY, NORMAL, ELEVATED |
| 9 | Metabolic pipeline bypassed CURATED layer | FEATURES | METABOLIC_FEATURES read directly from RAW_DATA | Created CURATED.METABOLIC_VISITS, refactored chain |
| 10 | Missing metabolic component scores NULL vs 0 | METRICS | Missing components scored 0 = optimistic bias | Changed to NULL when components missing |

### Documentation Fixes

| # | Issue | Fix |
|---|-------|-----|
| 11 | T12-T14 were assertions not real tests | Rewrote with actual validation logic |
| 12 | T15/T18 used invalid TABLE_TYPE='SEMANTIC VIEW' | Changed to SHOW SEMANTIC VIEWS approach |
| 13 | T19 referenced but never defined | Created: checks no LATEST/METADATA columns in semantic view |
| 14 | SEMANTIC_DEFINITIONS count stale (11 vs 41) | Updated to 41 |
| 15 | DOMAIN sample_values missing WELLNESS/METABOLIC | Added all 5 domains |
| 16 | SOURCE_SYSTEM sample_values missing CGM | Added CGM |
| 17 | Schema inventory omitted SEMANTIC schema | Added with correct object counts |
| 18 | Depresjon NULL dates not documented | Added as known issue |

---

## 15. Design Decisions & Trade-offs

### Views-Only Pipeline (No Materialization)

**Decision**: Every layer after RAW_DATA is SQL views, not tables or materialized views.

**Why**: Ensures pipeline consistency — fixing a bug in CURATED automatically propagates to FEATURES → METRICS → SEMANTIC without re-running ETL. Trade-off: query performance depends on warehouse size; complex queries scan the full pipeline.

### 28-Day Descriptive Baselines

**Decision**: Personal baselines use 28-day rolling averages (including current day).

**Why**: Longer windows are more stable. Including the current day makes baselines "descriptive" (what is normal) rather than "predictive" (what was normal before today). 10-observation minimum prevents unreliable baselines from small samples.

### Dual Z-Score Windows

**Decision**: 14-day window for recovery anomaly detection, 28-day window for baseline comparison.

**Why**: Recovery is an acute signal — a shorter window catches recent HR elevation faster. Baselines need stability — a longer window smooths out day-to-day variation. This is intentional and documented.

### Cohort Separation (Not a Design Choice)

The zero overlap between wellness and metabolic cohorts is a **data characteristic**, not a design decision. The research datasets come from completely different studies. The system enforces this boundary rather than pretending cross-domain data exists.

### PROVISIONAL Everything

**Decision**: All health state classifications are labeled PROVISIONAL.

**Why**: Thresholds (e.g., CRITICAL_DEBT when sleep debt > 10 hours) are engineering estimates, not clinically validated cutoffs. The PROVISIONAL label prevents downstream consumers from treating them as medical assessments.

---

## 16. Known Limitations

1. **No real-time data** — all data is historical research data from 2002-2021
2. **No cross-cohort linking** — a wellness subject has zero metabolic data and vice versa
3. **Depresjon NULL dates** — 3 Depresjon subjects have NULL observation dates
4. **Fitbit tables with 0 queries** — FITBIT_MINUTE_METRICS and FITBIT_HOURLY_METRICS loaded but not consumed by any view
5. **No formal constraints** — RAW_DATA tables have no NOT NULL or FK constraints; data quality is enforced at the view level
6. **Circadian features limited to PMData** — only 16 subjects have sleep timestamps needed for circadian analysis
7. **CGM_PATIENT_SUMMARY archived in place** — redundant with CGM_PATIENT_VISIT but retained for provenance
8. **Agent cannot execute SQL** — Cortex Agent generates SQL via Cortex Analyst but cannot run arbitrary user-provided SQL
9. **No streaming** — DATA_AGENT_RUN does not support streaming responses (set `stream: false`)

---

## 17. Future Roadmap

### P0 — Immediate
- Run agent evaluation against 25 test cases and iterate on verified queries
- Prune unnecessary synonyms in semantic views (Snowflake best practice)

### P1 — Near Term
- Population reference ranges (percentile bands across all subjects, not just personal baselines)
- Coaching instruction layer ("Your sleep debt is worsening — consider earlier bedtime")
- Streamlit UI improvements (charts, trends visualization)

### P2 — Medium Term
- Real AAYU user onboarding (production wearable integration)
- Dynamic table materialization for performance (replace views with incremental refresh)
- Cortex Search integration for unstructured health knowledge (research papers, guidelines)

### P3 — Long Term
- Multi-turn conversation threads with memory
- Proactive alerts ("Your recovery has been declining for 3 consecutive days")
- Integration with health coaching workflows

---

## 18. Appendix: Object Inventory

### WELLNESS_AI Database — All Objects

| Schema | Tables | Views | Semantic Views | Agents | Total |
|--------|--------|-------|---------------|--------|-------|
| RAW_DATA | 22 | 0 | 0 | 0 | 22 |
| IDENTITY | 2 | 1 | 0 | 0 | 3 |
| CURATED | 0 | 7 | 0 | 0 | 7 |
| FEATURES | 0 | 6 | 0 | 0 | 6 |
| METRICS | 0 | 10 | 0 | 0 | 10 |
| SEMANTIC | 2 | 4 | 3 | 1 | 10 |
| DEMO_SEMANTIC | 0 | 4 | 2 | 2 | 8 |
| **Total** | **26** | **32** | **5** | **3** | **66** |

### Agents

| Agent | Schema | Tools | Subjects | Purpose |
|-------|--------|-------|----------|---------|
| AAYU_RESEARCH_AGENT | SEMANTIC | 3 (Wellness, DataQuality, Metabolic) | 225 real | Internal research exploration |
| AAYU_DEMO_AGENT | DEMO_SEMANTIC | 2 (Wellness, Metabolic) | 12 synthetic | Lightweight demo |
| AAYU_PUBLIC_AGENT | DEMO_SEMANTIC | 2 (Wellness, Metabolic) | 12 synthetic | Hardened public-facing demo |

---

## 19. Appendix: Row Counts Across Pipeline

| Layer | Object | Rows |
|-------|--------|------|
| RAW | FITBIT_HEARTRATE | 3,644,219 |
| RAW | GARMIN_VIVOSMART | 8,188,778 |
| RAW | PMDATA_HEART_RATE | 20,997,512 |
| RAW | CGM_PATIENT_VISIT | 141 |
| RAW | DEPRESJON_ACTIGRAPHY | 1,571,706 |
| CURATED | DAILY_HEALTH_SUMMARY | 5,466 |
| CURATED | SLEEP_SESSIONS | 3,177 |
| CURATED | HEART_RATE_HOURLY | 75,859 |
| CURATED | METABOLIC_VISITS | 141 |
| FEATURES | SLEEP_FEATURES | 3,177 |
| FEATURES | ACTIVITY_FEATURES | 4,212 |
| FEATURES | HEART_RATE_FEATURES | 3,090 |
| FEATURES | METABOLIC_FEATURES | 141 |
| METRICS | PERSONAL_BASELINES | 10,479 |
| METRICS | AAYU_HEALTH_STATE | 4,478 |
| METRICS | METABOLIC_RISK_PIT | 141 |
| SEMANTIC | SUBJECT_HEALTH_CONTEXT | 4,478 |
| SEMANTIC | SUBJECT_DOMAIN_DETAIL | 12,615 |
| SEMANTIC | SUBJECT_DATA_QUALITY | 304 |
| SEMANTIC | SUBJECT_METABOLIC_CONTEXT | 141 |
| DEMO | SUBJECT_HEALTH_CONTEXT | 550 |
| DEMO | SUBJECT_METABOLIC_CONTEXT | 16 |

---

## 20. Appendix: Related Documents

| Document | Lines | Coverage |
|----------|-------|---------|
| `AAYU_HEALTH_INTELLIGENCE_v0.1.md` | 756 | Metric specifications, feature dictionary, coverage matrix, dependency graph, temporal leakage analysis, data quality |
| `AAYU_SEMANTIC_LAYER_v0.1.md` | 1,618 | Complete semantic view DDL, field dictionaries (54 fields × 17 attributes), lineage matrix, 19 automated tests, validation report |
| `AAYU_CORTEX_AGENT_v0.1.md` | 350 | Agent architecture, 22 verified queries, evaluation dataset, custom instructions, deployment guide |
| `AAYU_PROJECT_DOCUMENTATION_v1.0.md` | This doc | End-to-end project narrative covering the entire build process |

---

*Document generated October 2026. All data is from public research datasets. All health classifications are PROVISIONAL engineering prototypes. This is not a clinical system.*
