HECATE946 HOUSE EXTERIOR 2.5D — V1

This directory intentionally contains one master procedural exterior scene.

The existing exact house stays in:
    blender/house/house.blend

The exterior builder APPENDS only the house's:
    Architecture
    Windows
    Door
    Roof

It then creates a new modular scene around that source:
    WORLD_BACKGROUND
    WORLD_MIDGROUND__landscape
    WORLD_MIDGROUND__vegetation
    WORLD_FOREGROUND
    WORLD_HOUSE_SOURCE
    WORLD_SEASONAL
    WORLD_INTERACTION
    WORLD_CAMERAS
    WORLD_LIGHTS

There is one fixed camera for all four seasons. Geometry and plant locations stay
the same. Only seasonal materials, foliage visibility, accents, snow, lighting,
and window glow change.

OUTPUTS
    blender/house/exterior/exterior-25d.blend

    public/scenes/house/exterior/spring.png
    public/scenes/house/exterior/summer.png
    public/scenes/house/exterior/autumn.png
    public/scenes/house/exterior/winter.png

QUALITY
    PREVIEW  = 1280x720, Eevee
    WEB      = 2400x1350, Cycles
    FINAL    = 3200x1800, Cycles

The website component src/components/house/HouseExterior.astro switches the four
renders directly from html[data-season]. It is designed to consume exactly the
remaining flex height between the actual header and footer and uses centered
object-fit: cover, so narrow screens crop only the sides.
