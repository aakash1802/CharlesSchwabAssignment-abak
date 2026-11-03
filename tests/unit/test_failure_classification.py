"""Unit tests for failure classification heuristics."""

from __future__ import annotations

from agentic_engineer.llm.failures import (
    FailureCategory,
    classify_command_evidence,
    classify_from_message,
)


def test_command_failed_exit_alone_is_not_test_failure() -> None:
    assert classify_from_message("Command failed exit=4") != FailureCategory.TEST_FAILURE
    assert classify_from_message("Command failed exit=4") == FailureCategory.UNKNOWN
    assert (
        classify_command_evidence(exit_code=4, stdout="", stderr="")
        == FailureCategory.UNKNOWN
    )


def test_modulenotfound_is_dependency_failure() -> None:
    stderr = (
        "ImportError while loading conftest.py.\n"
        "E   ModuleNotFoundError: No module named 'sqlalchemy'\n"
    )
    assert (
        classify_command_evidence(exit_code=4, stdout="", stderr=stderr)
        == FailureCategory.DEPENDENCY_FAILURE
    )
    assert (
        classify_from_message(f"Command failed exit=4\n{stderr}")
        == FailureCategory.DEPENDENCY_FAILURE
    )


def test_pytest_assertion_is_test_failure() -> None:
    stdout = (
        "tests/test_services.py::test_validate_url FAILED\n"
        "E   AssertionError: assert False\n"
    )
    assert (
        classify_command_evidence(exit_code=1, stdout=stdout, stderr="")
        == FailureCategory.TEST_FAILURE
    )
    assert classify_from_message(stdout) == FailureCategory.TEST_FAILURE


def test_pytest_nodeid_failed_line_is_test_failure() -> None:
    blob = "FAILED tests/test_api.py::test_create_short_url - assert 500 == 201"
    assert classify_from_message(blob) == FailureCategory.TEST_FAILURE
    assert (
        classify_command_evidence(exit_code=1, stdout=blob, stderr="")
        == FailureCategory.TEST_FAILURE
    )


def test_timed_out_command_is_transient() -> None:
    assert (
        classify_command_evidence(
            exit_code=-1, stdout="", stderr="timed out", timed_out=True
        )
        == FailureCategory.TRANSIENT_PROVIDER
    )


def test_invalid_json_without_truncation_signal() -> None:
    msg = "LLM returned invalid JSON (Expecting value at line 1 column 1)."
    assert classify_from_message(msg) == FailureCategory.INVALID_STRUCTURED_OUTPUT


def test_unterminated_string_is_output_truncated() -> None:
    msg = "LLM returned invalid JSON (Unterminated string starting at at line 6 column 18)."
    assert classify_from_message(msg) == FailureCategory.OUTPUT_TRUNCATED


def test_did_not_contain_json_is_structured_output() -> None:
    assert (
        classify_from_message("Model response did not contain JSON")
        == FailureCategory.INVALID_STRUCTURED_OUTPUT
    )
