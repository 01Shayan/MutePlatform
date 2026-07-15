"""Startup splash / initialization screen (~1 second).

A lightweight loading entrance. The full brand banner is intentionally NOT shown here — it
debuts once on the Main Menu — so this screen stays a subtle, professional loading moment.
"""

from __future__ import annotations

import time

from rich.text import Text

from ..theme import Icon, console

_STEPS = ("Loading configuration", "Loading workspaces", "Loading integrations")
_CHECK = "✓"


def show(step_delay: float = 0.25) -> None:
    console.clear()
    console.print()
    console.print(Text(f"{Icon.BRAIN} Mute Platform", style="brand"), justify="center")
    console.print()
    console.print(Text("Initializing…", style="muted"), justify="center")
    console.print()

    for step in _STEPS:
        time.sleep(step_delay)
        console.print(
            Text.assemble((f"{_CHECK} ", "success"), (step, "value")), justify="center"
        )

    time.sleep(step_delay)
    console.print()
    console.print(Text("Ready", style="success"), justify="center")
    time.sleep(step_delay)
