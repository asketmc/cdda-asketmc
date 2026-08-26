# Release changelog and Windows publication

The fork has two complementary records:

- `PATCHNOTES_ADDITIVE_0G.md` is the curated, cumulative description of the fork.
- `CHANGELOG.md` and `doc/releases/<tag>.md` are generated, strict release deltas.

The generated history is deterministic. CI does not contact an external text generator, scrape mutable pull-request text, infer the previous release from tag names, or insert the current time. Reviewed JSON in the repository is the source of truth.

## Pull-request fragments

Every pull request adds `changelog/changes/pr-<number>.json`, including automated dependency updates. A fragment may contain multiple player or maintainer entries, so a pull request with several independently useful changes does not need to hide them behind one vague title.

Required entry fields are:

- a stable lowercase kebab-case `id`;
- one category from `Features`, `Content`, `Interface`, `Mods`, `Balance`, `Bugfixes`, `Performance`, `Build`, `Infrastructure`, or `I18N`;
- `players` or `maintainers` as the audience;
- a one-line summary;
- one of `save-compatible`, `new-world-recommended`, `new-world-required`, `not-applicable`, or `unknown` for compatibility.

Optional `details` and `known_limits` arrays provide the stricter information that should survive after the pull request is closed. A fragment may instead contain an explicit `skip.reason` when the change genuinely should not appear in release notes.

CI requires the fragment filename and embedded PR number to match. Existing fragments are immutable. The initial bootstrap is the only pull request allowed to add historical fragments, and `changelog/bootstrap.json` immutably binds that exceptional commit to PR #20.

Historical GitHub merge and squash subjects remain readable, but future changes enter `main` by squash merge only. The release chain derives a future squash commit's PR identity from the single immutable fragment added by that commit, so editing GitHub's squash subject cannot break the chain. Merge-commit and rebase merging are disabled. Branch protection requires linear history, a pull request, and the up-to-date `Portable contracts` check, applies to administrators, and forbids force-pushes and deletion. The push gate independently audits that exactly one reviewed integration reached `main` and repeats the fragment/history checks.

### Optional drafting assistance

A local drafting tool may propose fragment wording from a pull-request diff or summary. The maintainer must review the facts, audience, compatibility, and known limits before committing the JSON. CI and published output contain only the reviewed repository content, with no drafting-tool metadata or generated-by marker.

## Preparing a release

The release descriptor must be merged before its tag exists. Use a draft pull request so its number is known:

1. Start from current `origin/main` and open a draft release-preparation pull request.
2. Add the pull request's own fragment.
3. Run:

   ```sh
   python tools/release_changelog.py prepare \
     --tag v0.G-additive-YYYY.MM.DD.N \
     --title "CDDA 0.G Additive YYYY.MM.DD.N" \
     --date YYYY-MM-DD \
     --previous <current-published-tag> \
     --target origin/main \
     --release-pr <draft-pr-number>
   ```

4. Edit release-level `known_limits` or `validation` only when the generated defaults are incomplete, then run:

   ```sh
   python tools/release_changelog.py render-all
   python tools/release_changelog.py lint --check-generated
   ```

5. Review and merge the release-preparation pull request. Create the annotated tag on that exact `main` commit and push it.

`prepare` enumerates the first-parent PR integrations since the explicitly named published release. It neither chooses a previous tag nor trusts filesystem order. The tag gate repeats the range check and requires manifest PR order to match the exact integration order.

The unpublished failed tag `v0.G-additive-2026.08.26` is intentionally absent from `changelog/releases/index.json`. It is not a release boundary. `v0.G-additive-2026.08.26.1` explicitly follows the published `v0.G-additive-2026.08.25` release.

## Tag gate and immutable assets

Before downloading the compiler toolchain, a tagged run verifies:

- the tag resolves to the workflow commit and belongs to `main`;
- its source manifest is indexed and all generated Markdown is current;
- the explicitly named previous release exists on GitHub and is not a draft;
- every first-parent integration in the range has exactly one reviewed fragment.

The Windows build then copies `RELEASE_NOTES.md`, `CHANGELOG.md`, `PATCHNOTES_ADDITIVE_0G.md`, and `RELEASE_METADATA.json` into the distribution. Two clean release builds must produce identical executable and ZIP hashes.

Publication exposes five immutable assets:

- the Windows Tiles and Sound ZIP;
- `RELEASE_NOTES.md`;
- `RELEASE_MANIFEST.json` with full commit and artifact hashes;
- `BUILD_MANIFEST.txt` with build inputs and embedded-document hashes;
- `SHA256SUMS.txt`, which authenticates the other four assets.

The exact staged bundle is verified again on Windows, extracted, and run with `--check-mods dda`. After both first publication and a rerun, CI reads the release back and requires its title, body, five-name asset set, checksums, and every asset byte to match. It never clobbers or silently edits an existing release.
