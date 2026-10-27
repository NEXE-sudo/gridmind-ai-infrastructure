# GridMind code and asset provenance audit

**Review date:** 2026-10-27
**Scope:** checked-out public repository, tracked source/assets, frontend
dependency lock, Python lock, Git author metadata, and the linked upstream model
record. This is an evidence inventory, not legal advice or a license grant.

## Repository and ownership

- The GitHub repository
  [`NEXE-sudo/gridmind-ai-infrastructure`](https://github.com/NEXE-sudo/gridmind-ai-infrastructure)
  was public when checked on 2026-10-27. GitHub returned no detected repository
  license, and no tracked root or subdirectory `LICENSE`, `COPYING`, or
  `NOTICE` file was found.
- Git history contains multiple author identities, including `NEXE-sudo`,
  `NEXEYT`, and other historical identities. Commit metadata is not proof of
  copyright ownership, assignment, or permission to relicense.
- **Unclear / owner review required:** confirm who owns or has authority to
  license every inherited Scaler source file and binary asset, and obtain
  permission from any other contributors/rightsholders as necessary. Do not
  add a repository-wide open-source license until the owner has confirmed
  sufficient rights and compatibility. The absence of a license is not an
  assertion that any code is in the public domain.

## First-party and inherited source

| Scope | Evidence and status | Required action before public licensing |
|---|---|---|
| GridMind simulator, scheduler, benchmarks, API, dashboard, tests, and docs | Added and materially changed in the GridMind PR series; the merge history dates PRs #1–#6 to 2026-10-26 and 2026-10-27. No repository license or contributor license records are present in this checkout. | Confirm author/organization rights and contribution authorization before selecting a license. |
| Retained Scaler Energy Manager source, notebooks, scripts, UI, and configuration | Preserved as historical project code. There is no root license or per-file rights statement establishing redistribution or relicensing rights in the checked tree. | Obtain the original project owner’s permission and reconcile rights for all contributors. Do not imply the legacy project is GridMind runtime. |
| `Scaler_hackathon/lora_energy_grid/` and `checkpoint-20/` | Includes LoRA adapter weights, tokenizer/configuration files, a chat template, and training state. Its adapter README says the base is `TinyLlama/TinyLlama-1.1B-Chat-v1.0`, but its top-level `licence: license` value is not a usable grant; the checkpoint model card leaves the license and developer as “More Information Needed.” | Confirm who created/owns the adapter and the rights for the adapter, tokenizer/template, base-model-derived material, and training inputs. Exclude these files from a public package if rights cannot be established; do not delete inherited files as part of this audit. |
| `dataset_raw.jsonl`, `dataset_clean.jsonl` | Both tracked files were zero bytes on the review date. They contain no dataset records in this checkout. Their names/training scripts do not establish the provenance or rights of any data generated elsewhere. | Do not describe the empty files as a usable dataset. Review data sources, permissions, and personal-data risk before adding records. |

The official Hugging Face model API for
[`TinyLlama/TinyLlama-1.1B-Chat-v1.0`](https://huggingface.co/api/models/TinyLlama/TinyLlama-1.1B-Chat-v1.0)
reported `apache-2.0` on 2026-10-27. That metadata applies to the upstream
base-model repository; it does **not** establish ownership or a license for
GridMind's LoRA adapter, its training data, or other bundled artifacts.
GridMind's current Nebius adapter references a configurable NVIDIA Nemotron
model ID; this checkout does not bundle NVIDIA model weights or establish
that a live NVIDIA model request succeeded.

## Images, fonts, icons, and UI code

| Asset or code | Inventory finding | Status / next action |
|---|---|---|
| `Scaler_hackathon/plots/comparison.png`, `Scaler_hackathon/plots/lora_easy_rewards.png` | Two retained historical plot images. No adjacent attribution or creator/license record was identified. | Rights and source unclear; replace or exclude from a distributable/public demo if not cleared. |
| `Scaler_hackathon/agent-grid-view/public/placeholder.svg`, `favicon.ico` | Both are tracked public-directory assets. No creator or license metadata was found; neither is referenced in the checked `index.html` or frontend source. | Unused in the current dashboard; establish provenance or replace with newly created, documented assets before serving/redistributing them. |
| Fonts | No font binaries or `@font-face` declarations were found. CSS lists `Inter` followed by operating-system sans-serif fallbacks; no remote font URL was found in the checked frontend source. | No bundled font file identified. Confirm any recording/deployment does not introduce an unlicensed font asset. |
| UI primitives and icons | The dashboard has 49 files under `src/components/ui` and imports Radix primitives. The code follows common shadcn-style composition, but repository metadata does not identify the source/template commit or document per-file copying. `lucide-react` supplies UI icons. | Radix package metadata reports MIT; `lucide-react` package metadata reports ISC. Verify the origin/license of the local wrapper code and preserve required upstream notices when packaging. Avoid unlicensed logos or decorative assets. |

The checked `agent-grid-view/index.html` contains no favicon reference, and no
frontend source import for the two public-directory images was found. These
findings describe this checkout; they do not prove the assets' origin.

## Dependency license metadata

- `agent-grid-view/package-lock.json` contains 540 package entries with
  declared license metadata: 447 MIT, 23 Apache-2.0, 34 ISC, 10 BSD-2-Clause,
  7 BSD-3-Clause, 9 `Apache-2.0 AND MIT`, 3 BlueOak-1.0.0, 1 0BSD, 1
  `MIT AND ISC`, 1 Python-2.0, and 1 CC-BY-4.0. Three lock entries omit the
  field (`class-variance-authority`, `cross-spawn`, and `lucide-react`); the
  installed package metadata for the reviewed versions identifies them as
  Apache-2.0, MIT, and ISC respectively. These machine-readable declarations
  still require the normal package-notice/license review; they are not a
  complete legal compatibility analysis. The lock identifies
  `caniuse-lite` as CC-BY-4.0 (review attribution/notice requirements) and
  `@swc/core-*` platform packages as `Apache-2.0 AND MIT`; other declared
  licenses, including BlueOak-1.0.0, 0BSD, and Python-2.0, also need to remain
  in the reviewed inventory.
- `Scaler_hackathon/uv.lock` resolves 173 Python package/version entries but
  does not record license identifiers. No Python dependency license matrix
  is claimed from the lock file. Review the licenses/notices for the selected
  runtime and optional dependency groups independently before redistribution.
- Security dependency audits, when run, are not license-compliance audits.
  Preserve the npm and uv lock files and generate a reviewed SBOM/license
  inventory before a release if the owner authorizes one.

## Model, data, and third-party attribution obligations

- The existing LoRA metadata cites TinyLlama as its base and TRL as a training
  framework. Their licenses do not automatically cover project-authored
  weights, empty data placeholders, or other retained source.
- The runtime uses open-source SDKs and packages named in the dependency
  manifests. The NVIDIA and Nebius APIs/models are optional, external
  integrations, not bundled assets. Any eventual live use must comply with
  the provider/model terms and any attribution or usage conditions.
- No local model file, adapter, image, font, dataset record, or logo has been
  declared cleared solely because it is present in Git or a dependency
  install.

## Release gate

1. Repository owner confirms project ownership and authority to grant a
   repository license, including rights for inherited GridMind and Scaler
   contributions.
2. Resolve rights for the LoRA adapter/checkpoint, training inputs, plots,
   favicon, placeholder SVG, and local UI template/source.
3. Generate and review an SBOM with license texts/notices for the exact
   runtime and frontend dependency sets, including optional extras if
   distributed.
4. Only then add the owner-approved license and notices, or exclude items
   whose rights cannot be established. This PR adds no license and does not
   claim the repository is open source.
