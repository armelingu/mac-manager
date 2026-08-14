"""Unit tests for the pure helpers inside `macmanager.network`."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from io import StringIO
from types import SimpleNamespace

import pytest
from rich.console import Console

from macmanager.cache import clear_all
from macmanager.network import (
    NetworkInfo,
    _local_ip,
    _run,
    _signal_quality,
    _wifi_info,
    render_network_panel,
)


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


class TestRun:
    """`_run` é a fronteira de crash de todo shell-out de rede. Timeout
    ou binário ausente tem que virar string vazia — nunca uma exceção
    que derrube `mm` / `mm net` / `mm watch`."""

    def test_returns_stdout_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "macmanager.network.subprocess.run",
            lambda *args, **kwargs: SimpleNamespace(stdout="192.168.1.10\n"),
        )
        assert _run(["ipconfig", "getifaddr", "en0"]) == "192.168.1.10\n"

    @pytest.mark.parametrize(
        "exc",
        [
            subprocess.TimeoutExpired(cmd="system_profiler", timeout=5),
            FileNotFoundError("ipconfig"),
            OSError("permission denied"),
        ],
    )
    def test_swallows_expected_failures(
        self, monkeypatch: pytest.MonkeyPatch, exc: Exception
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise exc

        monkeypatch.setattr("macmanager.network.subprocess.run", boom)
        assert _run(["/usr/sbin/system_profiler", "SPAirPortDataType"]) == ""


class TestLocalIp:
    def test_empty_run_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("macmanager.network._run", lambda *args, **kwargs: "")
        assert _local_ip("en0") is None

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("macmanager.network._run", lambda *args, **kwargs: "  10.0.0.4\n")
        assert _local_ip("en0") == "10.0.0.4"


class TestWifiInfoDegrades:
    """`system_profiler` passa de 5s com frequência na primeira chamada.
    O coletor tem que devolver dict vazio para o painel mostrar '—'
    em vez de traceback."""

    @pytest.fixture(autouse=True)
    def _clear_wifi_cache(self) -> Iterator[None]:
        clear_all()
        yield
        clear_all()

    def test_empty_profiler_output_returns_empty_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("macmanager.network._run", lambda *args, **kwargs: "")
        assert _wifi_info() == {}

    def test_parses_ssid_from_profiler_block(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sample = (
            "Current Network Information:\n"
            "          HomeNet:\n"
            "            Security: WPA3 Personal\n"
            "            Channel: 36 (5GHz, 80MHz)\n"
            "            Signal / Noise: -55 dBm / -92 dBm\n"
            "            Transmit Rate: 1200\n"
        )
        monkeypatch.setattr("macmanager.network._run", lambda *args, **kwargs: sample)
        info = _wifi_info()
        assert info["ssid"] == "HomeNet"
        assert info["security"] == "WPA3 Personal"
        assert info["rssi"] == -55
        assert info["tx_rate"] == "1200"


class TestRenderNetworkPanel:
    """SSID com markup Rich não pode derrubar `mm net` / o painel de status."""

    def test_ssid_with_closing_tag_does_not_raise(self) -> None:
        info = NetworkInfo(
            interface="en0",
            local_ip="192.168.1.2",
            public_ip="1.2.3.4",
            ssid="My[/Home]WiFi",
            bssid=None,
            rssi=-50,
            noise=None,
            channel="36",
            tx_rate="1200",
            security="WPA3",
        )
        buf = StringIO()
        Console(file=buf, force_terminal=True, width=80).print(render_network_panel(info))
        out = buf.getvalue()
        assert "My" in out
        assert "WiFi" in out
