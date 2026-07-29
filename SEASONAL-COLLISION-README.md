# Seasonal collision update

## What changed

- Every season still uses exactly **100 collision bodies**.
- The invisible cursor influence radius is substantially larger.
- Nearby objects receive a smooth extra push across a wide area, so the cursor moves more of the field at once without creating a hard force boundary.
- The original gentle long-range pointer force remains intact.
- Seasonal object sizes, beach-ball spacing, and instant summer switching are unchanged.

## Install

```bash
unzip -o ~/Downloads/hecate946-seasonal-collision-larger-cursor-radius.zip
npm run dev
```

The Rapier dependency used by the collision page remains:

```bash
npm install @dimforge/rapier2d-compat@0.19.3
```
