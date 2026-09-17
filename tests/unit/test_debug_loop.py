"""Unit tests for failure fingerprinting and autonomous debug loop."""

from ai_java_engineer.agents.debugger.debug_agent import DebugAgent


def test_failure_fingerprint_generation():
    error_log = "[ERROR] /src/main/java/OrderController.java:[42,12] cannot find symbol\n  symbol: class OrderDTO"
    fp1 = DebugAgent.compute_fingerprint(error_log)

    assert fp1.error_type == "COMPILATION_ERROR"
    assert fp1.file == "/src/main/java/OrderController.java"
    assert fp1.line == 42
    assert len(fp1.fingerprint_hash) == 16

    # Verify determinism: identical error gives identical hash
    fp2 = DebugAgent.compute_fingerprint(error_log)
    assert fp1.fingerprint_hash == fp2.fingerprint_hash
