import pytest


@pytest.mark.eval
def test_eval_marker_is_collected() -> None:
    # Placeholder so `pytest -m eval` has something to collect until the real
    # recorded-fixture eval suite lands; a marker with zero matches is a
    # pytest failure (exit code 5), not a pass.
    assert True
