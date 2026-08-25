# Ultica HiRes common-terrain pilot

This private-fork experiment replaces nine frequently visible summer grass and
pavement sprites with reviewed 64x64 sources while retaining UltiCa's 32x32
logical footprint. Fifteen pavement connectivity sprites are copied at exact 2x
nearest-neighbour size so rotations and multitile joins remain unchanged.

The image-generation step is intentionally separate from the deterministic
build. Image models do not reproduce identical pixels from prompts alone, so the
nine files in `reviewed/` are the canonical inputs. `manifest.json` binds those
files and their original source pixels by SHA-256.

## Deterministic build and validation

From the repository root:

```text
python --version
python -m pip install -r tools/gfx_tools/ultica_hires/requirements.txt
python tools/gfx_tools/build_ultica_hires.py build
python tools/gfx_tools/build_ultica_hires.py validate
python tools/gfx_tools/test_build_ultica_hires.py
```

Python 3.10 through 3.13 is supported. Use the same `python` executable for
installing dependencies and running every command above.

`build` is idempotent. It resolves source sprites through the current
`tile_config.json`, generates `hires_pilot.png`, inserts one override sheet
before `fallback.png`, and updates `BACKPORT_MANIFEST.json`.

The runtime atlas is deterministic. Review-image labels use an available system
font, so their typography can vary across operating systems without changing
the reviewed sprites or runtime output.

## Generating another reviewed batch

1. Extract exact 32x32 references and 1024x prompt inputs:

   ```text
   python tools/gfx_tools/build_ultica_hires.py extract --output-dir build/ultica_hires
   ```

2. Submit the files in `build/ultica_hires/source1024/` to the image agent using
   `PROMPTS.md`. Store returned images as `<name>.png` in a local raw directory.

3. Run deterministic reduction and seam correction:

   ```text
   python tools/gfx_tools/build_ultica_hires.py finalize \
     --source-dir build/ultica_hires/source32 \
     --raw-dir build/ultica_hires/raw \
     --output-dir build/ultica_hires/candidates
   ```

4. Eye-review candidates at native and repeated-tile scale. Only then replace
   canonical files in `reviewed/` and update their hashes in `manifest.json`.

5. Rebuild, regenerate review images, and run validation:

   ```text
   python tools/gfx_tools/build_ultica_hires.py build
   python tools/gfx_tools/build_ultica_hires.py review
   python tools/gfx_tools/build_ultica_hires.py validate
   ```

Raw image-agent outputs are deliberately not committed. They are approximately
27 MB for this nine-sprite pilot and are not required to reproduce the accepted
runtime atlas. Preserve them as a release artifact if forensic provenance is
needed.
