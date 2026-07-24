#!/usr/bin/env bash
# Week 1 acceptance demonstration (§271): from a clean clone, prove that Forge builds
# and its Python/C++20 boundary works. This is deliberately narrow — it does not test
# any coordinator, protocol, scheduling, storage, or kernel behavior, because none of
# that exists yet.
#
# Steps: build the native extension, import forge, import forge_cpp and call its
# trivial scaffold function, run one Python unit test, run one C++ unit test.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

PASS=()
FAIL=()

step() {
  local name="$1"
  shift
  echo
  echo "=== ${name} ==="
  if "$@"; then
    PASS+=("${name}")
  else
    FAIL+=("${name}")
  fi
}

require_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  echo "uv not found on PATH. Install it: https://docs.astral.sh/uv/getting-started/installation/" >&2
  return 1
}

build_and_install() {
  uv sync --extra test
}

import_and_call_native_extension() {
  uv run python -c "
import forge
import forge_cpp

assert forge is not None
result = forge_cpp.add(2, 3)
assert result == 5, f'forge_cpp.add(2, 3) returned {result!r}, expected 5'
print(f'forge_cpp.add(2, 3) = {result}')
"
}

run_one_python_unit_test() {
  uv run pytest tests/python/test_smoke.py::test_forge_cpp_add_scaffold_function -v
}

build_and_run_one_cpp_unit_test() {
  cmake --preset debug -DFORGE_BUILD_BINDINGS=OFF -DFORGE_BUILD_BENCH=OFF
  cmake --build --preset debug --target forge_cpp_tests
  ctest --preset debug -R AddIsCorrect
}

step "require uv" require_uv
step "build native extension + editable install" build_and_install
step "import forge and forge_cpp, call trivial function" import_and_call_native_extension
step "run one Python unit test" run_one_python_unit_test
step "build and run one C++ unit test" build_and_run_one_cpp_unit_test

echo
echo "=== Smoke test summary ==="
for name in "${PASS[@]:-}"; do
  [ -n "${name}" ] && echo "PASS  ${name}"
done
for name in "${FAIL[@]:-}"; do
  [ -n "${name}" ] && echo "FAIL  ${name}"
done

if [ "${#FAIL[@]}" -gt 0 ]; then
  echo
  echo "SMOKE TEST: FAIL (${#FAIL[@]} of $((${#PASS[@]} + ${#FAIL[@]})) steps failed)"
  exit 1
fi

echo
echo "SMOKE TEST: PASS (${#PASS[@]} of ${#PASS[@]} steps passed)"
