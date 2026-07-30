# Green Room Coffee Table

This folder contains the standalone Blender generator for the tall, heavy African-blackwood table designed for the green room.

## Generated dimensions

- **Width:** 34 in / 0.8636 m
- **Depth:** 34 in / 0.8636 m
- **Height:** 31.5 in / 0.8001 m
- **Legs:** 6.25 in square
- **Chessboard target:** 22 in square
- **Extra tabletop width:** exactly 12 in

## Run in Blender

Open `coffee_table.py` in Blender's **Scripting** workspace and press **Run Script**.

The script automatically creates:

- `coffee_table.glb`
- `coffee_table.blend`
- `textures/african_blackwood_basecolor.png`
- `textures/african_blackwood_roughness.png`
- `textures/african_blackwood_normal.png`

Set `AUTO_RENDER = True` near the top of the Python file to additionally create a transparent `coffee_table.png` preview.

The GLB includes a single optimized table mesh plus these helper nodes:

- `ChessBoardAnchor`
- `ChessFocusTarget`
- `ChessApproachAnchor`

The camera and preview lights remain in the `.blend` and are not exported into the GLB.
