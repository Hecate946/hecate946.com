HECATE946 PROFESSIONAL EXTERIOR — BLENDER 5.2.0 LTS

WHAT THIS VERSION CHANGES
-------------------------
This is no longer a "primitive spheres + flat colors" exterior.

The final scene uses:
- exact current house generated from blender/house/house.py
- Poly Haven Tree Small 02 for the two framing trees
- Poly Haven Bermuda grass model tiled as the lawn
- Poly Haven Shrub 04 for the formal low shrubs
- Poly Haven Sorrel shrub for restrained spring/summer pink flowers
- Poly Haven Concrete Floor 01 PBR maps for the centered stone path
- Poly Haven Kloppenheim Pure Sky HDRI for real outdoor illumination/reflections
- Cycles + adaptive sampling + denoising
- real sun lighting for contact shadows
- physical rolling background terrain
- warm emissive window cards behind the existing windows
- a wide desktop render composed specifically for the space between header/footer
- one centered master camera so mobile crops only the sides

IMPORTANT
---------
The website already reads:
    public/scenes/house/exterior/{season}.png

So no website code change is needed for this pass. Refresh /house-preview after
rendering.

FIRST BUILD
-----------
From repo root:

python3 blender/house/exterior/download_exterior_assets.py

blender --background --python blender/house/house.py

HECATE_EXTERIOR_QUALITY=PREVIEW \
HECATE_EXTERIOR_SEASONS=spring \
blender --background --python blender/house/exterior/build_exterior_25d.py

Then inspect:
    http://localhost:4321/house-preview

ALL FOUR PREVIEW RENDERS
------------------------
./scripts/render-house-exterior.sh PREVIEW

WEBSITE-QUALITY CYCLES
----------------------
./scripts/render-house-exterior.sh WEB

FINAL MASTER
------------
./scripts/render-house-exterior.sh FINAL

EDITABLE SCENE
--------------
blender blender/house/exterior/exterior-pro.blend

The downloaded professional assets are cached under:
    blender/assets/exterior/polyhaven/
