import pytest
from forge.domain.digests import Digest


def test_of_bytes_round_trips_through_hashlib() -> None:
    digest = Digest.of_bytes(b"forge")
    assert digest.algorithm == "sha256"
    assert len(digest.hex_value) == 64
    assert str(digest) == f"sha256:{digest.hex_value}"


def test_rejects_unsupported_algorithm() -> None:
    with pytest.raises(ValueError, match="only sha256"):
        Digest(algorithm="md5", hex_value="a" * 64)


def test_rejects_wrong_length() -> None:
    with pytest.raises(ValueError, match="invalid sha256 digest length"):
        Digest(algorithm="sha256", hex_value="ab")


def test_rejects_non_hex_value() -> None:
    with pytest.raises(ValueError, match="hexadecimal"):
        Digest(algorithm="sha256", hex_value="z" * 64)


def test_equal_bytes_produce_equal_digests() -> None:
    assert Digest.of_bytes(b"same") == Digest.of_bytes(b"same")
    assert Digest.of_bytes(b"a") != Digest.of_bytes(b"b")
