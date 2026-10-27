# NVIDIA × Nebius Global AI Hackathon submission readiness

**Rules checked:** 2026-10-27
**Target track:** Best Apps and Agents
**Status:** implementation and local offline evidence prepared; external
integration, rights, hosted access, and submission actions remain incomplete.

## Authoritative rules checked

The official [Devpost rules](https://nebiusglobalaihackathon.devpost.com/rules)
were fetched on 2026-10-27. The rules state:

- The submission period ends **Friday, 2026-10-30 at 10:00 a.m. Pacific
  Time**. On that date Pacific Time is UTC−07:00; this is **2026-10-30
  17:00 UTC / 22:30 IST**. The official deadline is Pacific Time; the IST
  conversion is provided for operator convenience.
- A working project must run through a runtime Token Factory inference call
  or use Nebius AI Cloud compute, and use at least one NVIDIA open-source
  model. Best Apps and Agents specifically says to power the app with Nemotron
  through Token Factory. Deployment to Serverless Endpoints or Jobs is
  encouraged but not required.
- A Best Apps submission must provide a working demo/hosted app/test-build
  URL, a public code repository with an open-source license visible from the
  repository page, setup instructions, and a YouTube demo video under three
  minutes. The video must show the project functioning, be publicly visible,
  and avoid third-party trademarks/copyrighted material without permission.
- Entrants must select a track, provide feedback on tools/models/services
  used, and explain material changes if the project existed before the
  submission period. The project must be the entrant's original work, solely
  owned by the entrant, and not violate third-party rights.
- Judges must have free, unrestricted access to test the project through the
  end of the judging period. Stage One is pass/fail for theme fit and genuine
  use of required APIs/SDKs; Stage Two equally weights Technological
  Implementation, Design, Potential Impact, and Quality of the Idea.

Re-check the linked live rules and the Devpost entry form before submission;
this checklist records the page checked on the date above and is not a
substitute for the entrant's account-specific entry requirements.

## Requirement checklist

| Requirement | Status | Evidence / next action |
|---|---|---|
| Best Apps and Agents: useful app powered by Nemotron through Token Factory | **Blocked** | The adapter and explicit opt-in verifier exist, but no authorized key/configured model ID was available for this review. A runtime provider call has not been verified. See [model integration](MODEL_INTEGRATION.md). |
| Application runs on Nebius Token Factory or Nebius AI Cloud and uses an NVIDIA open model | **Blocked** | No real Token Factory inference request or Nebius AI Cloud execution/deployment is evidenced. Offline fallback is not the required runtime integration. |
| Local app installs and works consistently as documented | **Verified complete** | Clean-checkout steps, Python/API tests, frontend build, and offline demo reproduction are the local readiness targets. Record exact final CI/local check outputs with the PR before claiming this row complete. |
| Working demo, hosted application, or test-build URL for Best Apps | **Blocked** | The local URL is not publicly judge-accessible. An operator must deploy a suitable test build or provide an otherwise accessible demo and maintain it for the judging period. |
| Public source repository | **Verified complete** | GitHub reported `NEXE-sudo/gridmind-ai-infrastructure` public on 2026-10-27. |
| Repository open-source license visible on GitHub | **Blocked** | The repository has no detected license file or GitHub license metadata. The [provenance audit](PROVENANCE_AUDIT.md) identifies unresolved contribution/assets rights. Owner/legal clearance must precede any license grant. |
| Repository contains required source/assets and instructions | **Prepared but awaiting operator action** | README and reproducible offline evidence are provided, but some inherited assets have unclear provenance. Resolve/exclude uncleared material and verify the submitted source package. |
| README setup and run instructions | **Verified complete** | Root [README](../../README.md) includes locked install, tests, local startup, focused demo reproduction, primary suite reproduction, and limitations. |
| Public YouTube demo under three minutes showing the running app | **Prepared but awaiting operator action** | A 2:30 [storyboard](DEMO_SCRIPT.md) and actual offline evidence exist. The video has not been recorded, uploaded, or checked for public visibility and rights-cleared content. |
| Select the Best Apps and Agents track | **Prepared but awaiting operator action** | Track is the stated project target; the entrant must select it in the Devpost submission. |
| Provide tool/model/service feedback | **Prepared but awaiting operator action** | No live provider experience is claimed. The entrant must submit honest feedback about tools actually used; do not fabricate provider feedback. |
| Written explanation of material changes since the submission period began | **Prepared but awaiting operator action** | A fact-based PR timeline is below. Entrant must confirm it accurately describes the team's work and include it in the entry. |
| Registration and completed Devpost submission before deadline | **Prepared but awaiting operator action** | No account registration or submission is claimed. The authorized entrant/representative must complete required fields before the official deadline. |
| Entrant eligibility, sole ownership, authority to submit, and no disqualifying sponsor support | **Blocked** | These are entrant-specific representations. Owner/team representative must verify eligibility, rights, contributor permissions, and any support/conflict conditions. Engineering cannot establish them from Git metadata. |
| Free, unrestricted access for judging through the judging period | **Blocked** | No hosted demo/test-build exists. The entrant must provide working access, any required instructions, and maintain availability through the period in the official rules. |
| Judging criteria and Stage One baseline | **Verified complete** | Official rules checked: required runtime/API use and a genuine track-fit project are pass/fail; the four Stage Two criteria are equally weighted. Current live integration blocker puts Stage One fit/use at risk until resolved. |
| Submission deadline and time zone | **Verified complete** | Official rules: 2026-10-30 10:00 a.m. Pacific Time = 17:00 UTC = 22:30 IST. |

## Material changes to explain

The historical Scaler Energy Manager is preserved as a separate legacy
project; GridMind is a substantive data-centre simulation, not a superficial
name or UI change. The official submission period began 2026-08-26. The
GitHub PR history records these material changes during that period:

| Date (2026) | PR | Material change |
|---|---|---|
| Oct 26 | [#1](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/1) | Added a separate data-centre simulator/scheduler foundation, guarded model proposal path, API, tests, and plan while preserving the original grid project. |
| Oct 26 | [#2](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/2) | Delivered the GridMind lifecycle, heterogeneous GPU/power constraints, deterministic policies, API, React console, and benchmark platform. |
| Oct 26 | [#3](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/3) | Added a versioned ten-scenario paired benchmark suite, failure traces, more operational metrics, scenario API, and dashboard controls. |
| Oct 26 | [#4](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/4) | Corrected fixed-horizon accounting, infeasibility/deferral diagnoses, and pairing so unfinished work is not mislabeled as a crashed run. |
| Oct 27 | [#5](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/5) | Added scheduler-grounded feasible-candidate placement evidence, skip diagnostics, bounded API decision history, and dashboard trace rendering. |
| Oct 27 | [#6](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/6) | Hardened optional, explicit Nemotron verification, inference/fallback telemetry, proposal validation, and fair live-vs-baseline evaluation. No real provider request was made. |

This chronology is supported by merged PRs/commit dates, not a claim that the
new project has completed every hackathon requirement. The entrant must
confirm the material-change description and its authorship before submission.

## Evidence and limits

- The focused [offline demo report](../benchmarks/judge-demo/report.md),
  manifest, and raw run records are generated by the simulator for seed 7.
  Their reproducibility check compares a fresh execution and excludes only
  `experiment.created_at` and each `experiment.runs[].created_at`.
- The demo's Nemotron mode is deterministic fallback. It is not a live model
  response, a hosted Nebius run, or evidence of model benefit.
- Power, energy, facility price, failure traces, and workload results are
  synthetic. There is no physical cluster or facility integration.
- The [provenance audit](PROVENANCE_AUDIT.md) records unresolved ownership and
  asset questions. No repository license has been added or inferred.
- The video, hosted test URL, account registration/submission, license grant,
  live model request, and Nebius deployment are not complete.
