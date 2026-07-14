# Objective
Restore the unit test baseline after the recent provider routing and configuration refactor. Currently, 11 tests fail due to configuration schema changes, provider interface updates, and backend API initialization side-effects.

## Root Causes of Failures

### 1. Legacy Configuration Attribute Access
**Failing Tests:**
- `tests/unit/test_current_defaults.py::test_gpt_theme_defaults`
- `tests/unit/test_ingestion_network_data_extractor.py::test_defaults_are_preserved_for_ingestion_phase`

**Root Cause:**
The `ProjectDefaults` Pydantic model was recently updated to use a `ThemeProviderDefaults` sub-model (under the `theme_provider` field) instead of the previous `gpt` field. The unit tests were not updated and still attempt to access `ProjectDefaults.gpt`, resulting in an `AttributeError`.

### 2. Provider Interface Compliance in Fallback Wrapper
**Failing Tests:**
- `tests/unit/test_gpt_themes.py::test_generate_gpt_theme`

**Root Cause:**
`_ClientProvider` in `src/themes/gpt_themes.py` inherits from `BaseLLMProvider`. The `BaseLLMProvider` contract was recently updated to require a generic `generate()` method (for the benchmark pipeline). `_ClientProvider` does not implement `generate()`, causing a `TypeError` on instantiation.

### 3. Backend API Module-Level Initialization Side-Effects
**Failing Tests:**
- 8 tests in `tests/unit/test_backend_api.py`

**Root Cause:**
`backend/main.py` unconditionally calls `app = create_app()` at the module level. This instantiates the `ArtifactService` with `DEFAULT_CONFIG_PATHS`. During testing, one of the default config files (`configs/sample_twitter_reply.yml`) cannot be found or fails to load, throwing a `FileNotFoundError` on module import. This cascades and fails all 8 tests in `test_backend_api.py` that import `backend.main`.

## Proposed Fixes

### 1. Update Configuration Assertions
**Files to modify:**
- `tests/unit/test_current_defaults.py`
- `tests/unit/test_ingestion_network_data_extractor.py`

**Changes:**
- Update attribute access in tests from `config.gpt` to `config.theme_provider`.
- Assert on `theme_provider.model`, `theme_provider.temperature`, etc., according to the new `ThemeProviderDefaults` schema.

### 2. Implement `generate` on `_ClientProvider`
**Files to modify:**
- `src/themes/gpt_themes.py`

**Changes:**
- Add the `generate()` method to `_ClientProvider` to satisfy the `BaseLLMProvider` abstract contract.
- Have it raise `NotImplementedError` with a message like "Legacy _ClientProvider does not support generic generation" since this wrapper is only used for `generate_theme`.

### 3. Defer Backend API Config Loading or Handle Missing Files
**Files to modify:**
- `backend/artifact_service.py`
- (Optionally) `backend/main.py`

**Changes:**
- Modify `backend/artifact_service.py`'s `_load_runs` to handle missing default config paths gracefully during initialization (e.g., logging a warning or skipping missing files instead of crashing). This allows the API to still start in an empty state or with mock configurations for testing without crashing `backend/main.py` on import.

## Verification Plan

### Automated Tests
- Run `.venv/bin/python -m pytest tests/unit` to verify the test suite baseline returns to green (0 failed, 190+ passed).
- Specifically ensure `test_backend_api.py` correctly runs and passes.

## Completion Status
- **Status:** Completed (Phase 5B Architectural Cleanup Finished)
- **Outcome:** The unit test baseline was successfully restored and then architecturally cleaned up. All 197 tests pass.
  - Replaced legacy `gpt` configuration assertions with `theme_provider` equivalents.
  - Removed `_ClientProvider` entirely because it bypassed provider routing.
  - Refactored `generate_gpt_theme` and `call_gpt_theme_api` to resolve their provider using `build_theme_provider(default_config)` instead of hardcoding model, seed, and temperature.
  - Updated `tests/unit/test_gpt_themes.py` to mock the provider factory (`build_theme_provider`) rather than injecting a raw OpenAI client.
  - Refined `backend/artifact_service.py` to only swallow `FileNotFoundError` if the missing config is one of the default sample configs, preventing configuration defects from being hidden.
