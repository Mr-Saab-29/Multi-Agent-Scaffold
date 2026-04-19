# Smart Execution Policy

This project supports stage-level model routing, cache reuse, and reviewer gating.

## Goals
- reduce API calls and cost
- keep quality where it matters
- preserve stable typed outputs

## Controls
Configure in `.env`:

```env
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MODEL_PLANNER=
GEMINI_MODEL_ARCHITECT=
GEMINI_MODEL_SCHEMA=
GEMINI_MODEL_API=
GEMINI_MODEL_FRONTEND=
GEMINI_MODEL_REVIEWER=
SMART_ENABLE_STAGE_CACHE=true
SMART_REVIEWER_ON_CLEAN=false
```

If a stage-specific variable is empty, it falls back to `GEMINI_MODEL`.

## Recommended Model Routing
Use model names available in your account (`list_models`), then map by stage:

- `planner`: fast/cheap flash-lite model
- `architect`: higher-quality flash/pro model (most important design stage)
- `schema`: higher-quality flash/pro model (consistency critical)
- `api`: flash model
- `frontend`: flash-lite or flash model
- `reviewer`: flash-lite (or skip when clean)

## Suggested Presets

### 1. Cost-first demo preset
```env
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MODEL_ARCHITECT=
GEMINI_MODEL_SCHEMA=
SMART_ENABLE_STAGE_CACHE=true
SMART_REVIEWER_ON_CLEAN=false
```

### 2. Balanced preset
```env
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MODEL_ARCHITECT=gemini-2.5-flash
GEMINI_MODEL_SCHEMA=gemini-2.5-flash
GEMINI_MODEL_API=gemini-2.5-flash-lite
GEMINI_MODEL_FRONTEND=gemini-2.5-flash-lite
GEMINI_MODEL_REVIEWER=gemini-2.5-flash-lite
SMART_ENABLE_STAGE_CACHE=true
SMART_REVIEWER_ON_CLEAN=false
```

### 3. Quality-first preset
```env
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MODEL_ARCHITECT=gemini-2.5-pro
GEMINI_MODEL_SCHEMA=gemini-2.5-pro
GEMINI_MODEL_API=gemini-2.5-flash
GEMINI_MODEL_FRONTEND=gemini-2.5-flash
GEMINI_MODEL_REVIEWER=gemini-2.5-flash
SMART_ENABLE_STAGE_CACHE=true
SMART_REVIEWER_ON_CLEAN=true
```

## Notes
- stage cache currently applies to `planner`, `architect`, `schema`.
- reviewer can be skipped automatically when validation is clean.
- retries/backoff are controlled by `GEMINI_MAX_RETRIES` and delay settings.
