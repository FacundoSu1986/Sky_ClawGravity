# CODE_REVIEW_RESOLUTION.md — PR #58 Critical Findings Fix Plan

## Executive Summary

Four critical design flaws detected in PR #58 (`claude/dazzling-maxwell-f3fc1a`) require specification-driven fixes before Phase 2 (execution). All changes preserve backward compatibility while enforcing correctness invariants.

---

## Finding 1: Pydantic Schema Validation Failure

**Issue**: `action_type="loop_detected"` does not exist in `HitlApprovalRequest` schema.

**Root Cause** (state_graph.py:998–1002):
```python
state["hitl_request"] = {
    "action_type": "loop_detected",  # ❌ NOT in Literal["download_external", "destructive_xedit", "circuit_breaker_halt"]
    "reason": str(exc),
    "tool_name": exc.tool_name,      # ❌ These fields don't belong at root level
    "occurrences": exc.occurrences,
}
```

**Expected Schema** (core/models.py):
```python
class HitlApprovalRequest(BaseModel):
    action_type: Literal["download_external", "destructive_xedit", "circuit_breaker_halt"]
    reason: str
    context_data: dict[str, Any]  # ← metadata goes HERE
```

**Fix**:
- **File**: `sky_claw/orchestrator/state_graph.py`, lines 997–1002
- **Action**: Replace root-level fields with context_data container
- **New Code**:
  ```python
  state["hitl_request"] = {
      "action_type": "circuit_breaker_halt",
      "reason": str(exc),
      "context_data": {
          "trip_reason": "Loop detected",
          "tool_name": exc.tool_name,
          "occurrences": exc.occurrences,
      },
  }
  ```

---

## Finding 2: Missing Null Check Before Guardrail Dispatch

**Issue** (state_graph.py:990): Code forces `tool_name or ""`, passing empty string to guardrail. Violates design invariant: "never invoke guardrail with invalid data."

**Root Cause** (StateGraphIntegration._on_dispatching, lines 987–990):
```python
tool_name = state.get("tool_name")
payload = state.get("tool_payload") or {}
try:
    self.state_graph.loop_guardrail.register_and_check(tool_name or "", payload)  # ❌
```

**Fix**:
- **File**: `sky_claw/orchestrator/state_graph.py`, lines 987–1002
- **Action**: Add null check; abort dispatch on missing tool_name
- **New Code**:
  ```python
  tool_name = state.get("tool_name")
  payload = state.get("tool_payload") or {}
  
  # Validate tool_name before guardrail invocation
  if not tool_name or not isinstance(tool_name, str):
      state["last_error"] = "tool_name is None or invalid"
      state["tool_result"] = {
          "status": "error",
          "error": "Tool dispatch aborted: tool_name is missing or invalid",
      }
      return
  
  try:
      self.state_graph.loop_guardrail.register_and_check(tool_name, payload)
  except CircuitBreakerTrippedError as exc:
      # ... rest of exception handling
  ```

---

## Finding 3: Consecutive Detection Logic Is Incorrect

**Issue** (loop_guardrail.py:57): Uses `self._history.count(action_hash)` which counts *all* occurrences in the deque, not *consecutive* ones.

**Symptom**: Pattern `[A, B, A, A]` incorrectly fires the breaker (2 total A's after adding the 3rd → count ≥ max_repeats), when it should only fire if last N elements are identical.

**Root Cause** (AgenticLoopGuardrail.register_and_check, lines 55–67):
```python
self._history.append(action_hash)
occurrences = self._history.count(action_hash)  # ❌ Counts all A's, not just trailing A's

if occurrences >= self._max_repeats:
    logger.critical(
        "Loop Detectado: el agente intentó ejecutar %s %d veces seguidas.",  # "seguidas" = consecutive
        tool_name,
        occurrences,
    )
```

**Expected Logic**: Check if the *last* `max_repeats` elements of the deque are all identical.

**Fix**:
- **File**: `sky_claw/security/loop_guardrail.py`, lines 55–67
- **Algorithm**: Compare the last `max_repeats` elements using slice operations
- **New Code**:
  ```python
  self._history.append(action_hash)
  
  # Check if the last max_repeats elements are all identical (consecutive detection)
  if len(self._history) >= self._max_repeats:
      last_n = list(self._history)[-self._max_repeats:]
      if all(h == last_n[0] for h in last_n):
          logger.critical(
              "Loop Detectado: el agente intentó ejecutar %s %d veces seguidas consecutivas. Activando cortacircuitos cognitivo.",
              tool_name,
              self._max_repeats,
          )
          self._history.clear()
          raise CircuitBreakerTrippedError(
              f"Has entrado en un bucle intentando usar '{tool_name}'. "
              "DETENTE. Solicita asistencia humana (HITL) inmediatamente.",
              tool_name=tool_name,
              occurrences=self._max_repeats,
          )
  ```

---

## Finding 4: Missing Test Coverage for Non-Consecutive Patterns

**Issue** (tests/test_loop_guardrail.py): No explicit test demonstrating that non-consecutive repeats do NOT trigger the breaker.

**Test Case Required**:
- **Pattern**: `[A, B, A, A]` (A appears 3 times but NOT consecutively at the start)
- **Expected**: GuardRail does NOT trip ✓
- **Current**: May incorrectly trip ✗

**Fix**:
- **File**: `tests/test_loop_guardrail.py`
- **New Test**:
  ```python
  def test_non_consecutive_pattern_does_not_trip():
      """Verify that non-consecutive repeats do not trigger the breaker.
      
      Pattern: A (registered), B (registered), A (registered), A (registered)
      Expected: No CircuitBreakerTrippedError raised because A is not in the last 3 slots consecutively.
      """
      guardrail = AgenticLoopGuardrail(max_repeats=3, window_size=5)
      
      # Register A
      guardrail.register_and_check("tool_a", {"arg": "value"})
      # Register B
      guardrail.register_and_check("tool_b", {"arg": "other"})
      # Register A again (breaking the sequence)
      guardrail.register_and_check("tool_a", {"arg": "value"})
      # Register A third time (still not consecutive from start)
      guardrail.register_and_check("tool_a", {"arg": "value"})
      
      # At this point, history is [hash(A), hash(B), hash(A), hash(A)]
      # The last 3 elements are [hash(B), hash(A), hash(A)] — NOT all identical
      # So the breaker should NOT trip
      
      snapshot = guardrail.snapshot()
      assert len(snapshot) == 4
      # Verify guardrail is still active (not cleared)
      assert len(guardrail._history) == 4
  
  def test_consecutive_pattern_trips():
      """Verify that consecutive repeats DO trigger the breaker.
      
      Pattern: A, A, A (three consecutive identical actions)
      Expected: CircuitBreakerTrippedError raised on the 3rd attempt.
      """
      guardrail = AgenticLoopGuardrail(max_repeats=3, window_size=5)
      
      guardrail.register_and_check("tool_a", {"arg": "value"})
      guardrail.register_and_check("tool_a", {"arg": "value"})
      
      with pytest.raises(CircuitBreakerTrippedError) as exc_info:
          guardrail.register_and_check("tool_a", {"arg": "value"})
      
      assert exc_info.value.tool_name == "tool_a"
      assert exc_info.value.occurrences == 3
      # Verify history was cleared after trip
      assert guardrail.snapshot() == ()
  ```

---

## Summary of Changes

| File | Lines | Issue | Fix |
|------|-------|-------|-----|
| `state_graph.py` | 997–1002 | Invalid `action_type="loop_detected"` | Change to `"circuit_breaker_halt"`, move fields to `context_data` |
| `state_graph.py` | 987–1002 | Missing null check before guardrail | Add validation, abort dispatch, set `last_error` and `tool_result` |
| `loop_guardrail.py` | 55–67 | Non-consecutive detection | Replace `count()` with last-N slice comparison |
| `test_loop_guardrail.py` | (append) | Missing non-consecutive test | Add `test_non_consecutive_pattern_does_not_trip()` |

---

## Consecutive Detection Algorithm (Detailed)

**Python logic** (used in loop_guardrail.py lines 55–62):

```python
# After appending the new action hash to self._history:
if len(self._history) >= self._max_repeats:
    last_n = list(self._history)[-self._max_repeats:]
    if all(h == last_n[0] for h in last_n):
        # All last N elements are identical → trip the breaker
```

**Why this works**:
- `list(self._history)[-self._max_repeats:]` extracts the last N elements as a list
- `all(h == last_n[0] for h in last_n)` returns True only if every element matches the first
- This guarantees *consecutive* repetition, not total count

**Example with max_repeats=3**:
- History: `[X, Y, Z, A, A]` → last 3 = `[Z, A, A]` → NOT identical (Z ≠ A) → no trip ✓
- History: `[X, Y, Z, A, A, A]` → last 3 = `[A, A, A]` → all identical → trip ✓

---

## Specification Status

✅ **Phase 1 Complete**: All 4 findings analyzed with exact line numbers and corrected code.
⏸️ **Awaiting Approval**: Execute Phase 2 only after user confirms:

> "Spec Aprobado. Ejecuta las correcciones, corre ruff, pytest y haz commit."

