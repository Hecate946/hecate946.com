Checkerboard V11 update
======================

Included files:
- blender/checkerboard_room_v11_no_chandelier_shared_overhead_light.py
- src/components/rooms/CheckerboardScene.svelte
- src/components/rooms/CheckerboardRoom.svelte

What changed:
- Removed the chandelier entirely from the Blender-generated room.
- Replaced the previous two-light rig with one simple exported warm overhead spotlight:
  Room_Overhead_Warm_Spot.
- Kept Blender and the website aligned by using only that exported GLB light.
- Website code now hides any old chandelier geometry and disables any non-room lights.

How to use:
1. In Blender, open your project and run blender/checkerboard_room_v11_no_chandelier_shared_overhead_light.py
   from the Scripting workspace.
2. Export the WEB_EXPORT collection as checkerboard.glb with:
   - Active Collection
   - Include Nested Collections
   - Materials
   - UVs
   - Normals
   - Apply Modifiers
   - Punctual Lights
3. Replace public/models/checkerboard.glb in the website project.
4. From the website project root, unzip these src/components files into place.
