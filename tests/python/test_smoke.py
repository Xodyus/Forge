"""Week 1 acceptance test (§271 item 5): proves forge imports and the forge_cpp
native extension is built, importable, and callable. Not a semantics test — no
domain logic exists yet to test.
"""

import forge
import forge_cpp


def test_forge_package_imports() -> None:
    assert forge is not None


def test_forge_cpp_add_scaffold_function() -> None:
    assert forge_cpp.add(2, 3) == 5
