from forge.domain.errors import ErrorClass, ErrorEnvelope


def test_public_dict_truncates_message_and_hides_nothing_else() -> None:
    envelope = ErrorEnvelope(
        code="E_KERNEL_DOMAIN",
        classification=ErrorClass.DETERMINISTIC_KERNEL,
        message="x" * 2_000,
        retryable=False,
        details={"partition_id": "p-0"},
    )
    public = envelope.public_dict()
    assert len(public["message"]) == 1_024
    assert public["classification"] == "deterministic_kernel"
    assert public["retryable"] is False
    assert public["details"] == {"partition_id": "p-0"}


def test_all_23_error_classes_present() -> None:
    # §23 Table 13 names eight classes; this pins the count so a future edit that
    # silently drops or renames one fails loudly here instead of downstream.
    assert {member.value for member in ErrorClass} == {
        "validation",
        "deterministic_kernel",
        "transient_worker",
        "lease_loss",
        "storage_publication",
        "protocol",
        "cancellation",
        "internal_invariant",
    }
