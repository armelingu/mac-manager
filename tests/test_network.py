"""Unit tests for the pure helpers inside `macmanager.network`."""

from __future__ import annotations

import pytest

from macmanager.network import _signal_quality


class TestSignalQuality:
    """`_signal_quality(rssi)` buckets Wi-Fi RSSI (dBm, negative) into a
    label + Rich color. Thresholds from the source:

        rssi is None  -> ("—", "dim")
        rssi >= -55   -> ("Excellent", "green")
        rssi >= -67   -> ("Good", "green")
        rssi >= -75   -> ("Fair", "yellow")
        else          -> ("Weak", "red")
    """

    def test_none_returns_placeholder(self) -> None:
        assert _signal_quality(None) == ("—", "dim")

    @pytest.mark.parametrize("rssi", [-30, -40, -55])
    def test_excellent(self, rssi: int) -> None:
        assert _signal_quality(rssi) == ("Excellent", "green")

    @pytest.mark.parametrize("rssi", [-56, -60, -67])
    def test_good(self, rssi: int) -> None:
        assert _signal_quality(rssi) == ("Good", "green")

    @pytest.mark.parametrize("rssi", [-68, -72, -75])
    def test_fair(self, rssi: int) -> None:
        assert _signal_quality(rssi) == ("Fair", "yellow")

    @pytest.mark.parametrize("rssi", [-76, -80, -100])
    def test_weak(self, rssi: int) -> None:
        assert _signal_quality(rssi) == ("Weak", "red")

    def test_positive_rssi_is_treated_as_excellent(self) -> None:
        # RSSI should always be negative in practice, but the function
        # doesn't special-case positive values — they trivially satisfy
        # `>= -55`.
        assert _signal_quality(0) == ("Excellent", "green")
