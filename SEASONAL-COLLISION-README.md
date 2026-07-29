# Seasonal collision and homepage summer update

## What changed

- The collision page now uses a `1.72x` invisible collider radius. Beach balls remain the same visible size, but the collision cloud has substantially more breathing room.
- The homepage summer shower has its original falling, gravity, wall-bounce, floor-bounce, energy-loss, and fade behavior restored.
- Only the homepage beach-ball rotation is shared with the collision simulator: both use the same continuous WebGL quaternion renderer and the same sleep/wake rotation mechanics.
- The homepage no longer uses the collision page's D3 centering or pointer-repulsion movement.
- Spring, autumn, and winter shower behavior is unchanged.

## Install

```bash
unzip -o ~/Downloads/hecate946-seasonal-collision-homepage-bounce-rotation.zip
npm run dev
```

The Rapier dependency used by the collision page remains:

```bash
npm install @dimforge/rapier2d-compat@0.19.3
```
