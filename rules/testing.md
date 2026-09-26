---
name: Behavioral Testing Standards
description: Enforces behavioral testing over implementation testing, requires sad paths, and minimizes brittle mocks.
trigger: model_decision
---
# Testing Standards & Philosophy

> **Role**: This rule enforces senior-level testing practices, prioritizing tests that provide high confidence while remaining resilient to refactoring.

## 1. Test Behaviors, Not Implementation
- **Treat as a Black Box**: Test the public API or observable behavior of the script or module. Do not assert on internal state or private helper functions.
- **Resilience**: A test should only fail if the *outcome* changes, not if the *internal logic* is refactored. 

## 2. Minimal Mocking
- **Real Over Fake**: Avoid heavy mocking frameworks or mocking internal dependencies where possible. Prefer using real data objects, in-memory databases, or lightweight stubs.
- **Mock at the Boundary**: Only mock external network calls, file system boundaries, or heavy I/O that makes tests flaky or slow.

## 3. Comprehensive Coverage (Sad Paths)
- **Beyond the Happy Path**: Always ensure tests cover boundary conditions, edge cases, and "sad paths" (e.g., malformed input, timeout errors, missing files).
- **Error Assertions**: When testing scripts that can fail, assert that the exact error type or message is returned/thrown, rather than just asserting a generic failure.

## 4. Script & CLI Testing
- **Integration Mindset**: When testing local scripts or CLIs, test them by invoking the entry function with various arguments and capturing stdout/stderr/exit codes, ensuring they behave correctly from a user's perspective.
- **Setup/Teardown**: Ensure tests clean up after themselves (e.g., deleting temporary files created during script execution).
