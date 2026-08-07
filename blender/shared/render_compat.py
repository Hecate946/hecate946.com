"""
Blender render-engine compatibility helpers for hecate946.com.

Why this exists
---------------
Blender's Eevee enum identifier has changed across versions. Some builds expose
BLENDER_EEVEE, others BLENDER_EEVEE_NEXT. Assigning an unsupported enum raises
TypeError immediately.

Project rule:
    Never hard-code an Eevee render-engine enum without interrogating the
    running Blender build first.

This module is intentionally tiny and dependency-free so every Blender builder
can share the same compatibility rule.
"""

from __future__ import annotations

import bpy


def available_render_engines(scene: bpy.types.Scene) -> set[str]:
    try:
        prop = scene.render.bl_rna.properties["engine"]
        return {item.identifier for item in prop.enum_items}
    except Exception:
        # Conservative fallback for unusual builds.
        return {"BLENDER_EEVEE", "BLENDER_WORKBENCH", "CYCLES"}


def set_best_eevee(scene: bpy.types.Scene) -> str:
    engines = available_render_engines(scene)

    for candidate in (
        "BLENDER_EEVEE_NEXT",
        "BLENDER_EEVEE",
        "BLENDER_WORKBENCH",
        "CYCLES",
    ):
        if candidate in engines:
            scene.render.engine = candidate
            return candidate

    raise RuntimeError(
        "No supported render engine found. Blender reports: "
        + ", ".join(sorted(engines))
    )


def set_cycles_or_best(scene: bpy.types.Scene) -> str:
    engines = available_render_engines(scene)
    if "CYCLES" in engines:
        scene.render.engine = "CYCLES"
        return "CYCLES"
    return set_best_eevee(scene)
