# -*- coding: utf-8 -*-
\"\"\"
UI Block Probe (Heartbeat)

Amaç:
- UI thread'in bloklanıp bloklanmadığını pratikte görmek.
- RENFORGE_UI_PROBE=1 ortam değişkeni ile aktif olur.

Nasıl yorumlanır?
- Konsolda "[UI BLOCK] dt=XXXXms ..." görüyorsan, UI thread o anda kilitlenmiştir.
\"\"\"
from __future__ import annotations

import os
from PySide6.QtCore import QTimer, QElapsedTimer

_TIMER_HOLDER = None  # GC yemesin

def install_ui_block_probe(threshold_ms: int = 250, interval_ms: int = 100, enabled: bool | None = None) -> None:
    global _TIMER_HOLDER

    if enabled is None:
        v = os.getenv("RENFORGE_UI_PROBE", "").strip().lower()
        enabled = v in {"1", "true", "yes", "on"}

    if not enabled:
        return

    t = QElapsedTimer()
    t.start()

    timer = QTimer()
    timer.setInterval(interval_ms)

    last = [t.elapsed()]

    def beat():
        now = t.elapsed()
        dt = now - last[0]
        last[0] = now
        if dt > threshold_ms:
            print(f"[UI BLOCK] dt={dt}ms at {now}ms")

    timer.timeout.connect(beat)
    timer.start()

    _TIMER_HOLDER = timer
