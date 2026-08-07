"""Compatibility launcher for the current Hecate946 ballroom.

The ballroom no longer uses the old shared 360-degree hall shell. Its source is
``build_ballroom_25d.py``, which creates authored Cycles/Eevee still views for
the rendered-world pipeline.
"""

from pathlib import Path
import runpy

SCRIPT = Path(__file__).resolve().with_name("build_ballroom_25d.py")
runpy.run_path(str(SCRIPT), run_name="__main__")
