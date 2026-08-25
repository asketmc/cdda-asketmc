# Ultica HiRes pilot art direction

Each input was the exact 32x32 UltiCa sprite enlarged to 1024x1024 with
nearest-neighbour scaling.

## Summer grass variants

Use case: precise-object-edit

Asset type: seamless 64x64 top-down terrain sprite for Cataclysm-DDA UltiCa.

Faithfully re-render the same olive-green summer grass tile at higher source
density, adding restrained fine blades and natural ground microtexture that
remains legible when reduced to 64x64. Preserve each variant's different random
texture distribution.

Preserve average colour, brightness, contrast, and subdued tone. The tile must
be seamless on every edge and have uniform density. Do not add a focal object,
transparency, directional lighting, shadows, borders, text, watermarks, flowers,
stones, paths, dirt patches, objects, creatures, large blades, gradients, or
perspective.

## Pavement variants

Use case: precise-object-edit

Asset type: seamless 64x64 top-down road terrain sprite for Cataclysm-DDA
UltiCa.

Faithfully re-render the same plain grey asphalt at higher source density,
adding restrained fine aggregate, subtle granular wear, and small-scale tonal
variation that remains legible at 64x64.

Preserve average neutral-grey colour, brightness, low contrast, and subdued
tone. The tile must be seamless on every edge. Do not add transparency,
directional lighting, shadows, borders, text, watermarks, paint, cracks,
potholes, stains, tracks, debris, objects, large stones, gradients, or
perspective.

## Yellow pavement marker

Use case: precise-object-edit

Asset type: seamless 64x64 top-down marked-road terrain sprite for
Cataclysm-DDA UltiCa.

Re-render the grey asphalt at higher source density while preserving one
centred muted-yellow square dash in the same position, axis alignment, size
proportion, and shape.

The generated marker geometry drifted during reduction, so the accepted sprite
uses the reviewed `pavement_1` texture as its background and restores the
original marker mask at exact 2x geometry.

## Deterministic post-processing

- Select a detailed 64x64 crop with low opposite-edge error.
- Blend generated high-frequency detail over the original low-frequency form.
- Match mean colour and contrast to the original sprite.
- Apply periodic-plus-smooth frequency-domain boundary correction.
- Restore functional marker geometry from the original sprite.
- Copy non-centre pavement multitile dependencies at exact 2x nearest-neighbour
  size.
