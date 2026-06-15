Phase-specific instructions for the **Objectives** phase. Extends [../CLAUDE.md](../CLAUDE.md).

## Purpose

This phase defines **what** we're building and **why**. Focus on clarity, measurability, and alignment with stakeholder needs.

## Phase artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| Stakeholders | [`stakeholders.md`](stakeholders.md) | Roles with interests and influence |
| Goals | [`goals/`](goals/) | High-level outcomes |
| User Stories | [`user-stories/`](user-stories/) | User-facing capabilities |
| Requirements | [`requirements/`](requirements/) | Testable system requirements |
| Assumptions | [`assumptions/`](assumptions/) | Beliefs taken as true but not verified |
| Constraints | [`constraints/`](constraints/) | Hard limits on design and implementation |

---

## AI Guidelines

### Per-artifact guidance

**Stakeholders**: ask who uses, funds, operates, or is affected by the system. Record influence level honestly — it drives conflict resolution. Add entries to [`stakeholders.md`](stakeholders.md).

**Goals**: decompose vague ideas into concrete, measurable outcomes. Use MoSCoW priority consistently.
Status lifecycle: `Draft → Approved → Achieved → Deprecated`. Only a human can approve or deprecate. The agent marks `Achieved` when all success criteria are met (linked requirements implemented).

**User Stories**: use "As a [role], I want [capability], so that [benefit]." The role must be an existing stakeholder ID. Acceptance criteria at the story level are high-level; detailed criteria live in requirements.
Status lifecycle: `Draft → Approved → Implemented → Deprecated`. Only a human can approve or deprecate. The agent marks `Implemented` when all linked requirements reach `Implemented`.

**Requirements**: use clear, testable language (not "should be fast" — use "response time < 200ms at p95"). Choose the correct requirement class.
Requirement classes: `REQ-F` Functional, `REQ-PERF` Performance, `REQ-SEC` Security, `REQ-REL` Reliability, `REQ-USA` Usability, `REQ-MNT` Maintainability, `REQ-PORT` Portability, `REQ-SCA` Scalability, `REQ-COMP` Compliance.
Status lifecycle: `Draft → Approved → Implemented → Deprecated`. Only a human can approve or deprecate. The agent marks `Implemented` when all linked tasks reach Done.

**Assumptions**: always record the risk level (what happens if wrong?) and a verification plan when possible.
Status lifecycle: `Unverified → Verified | Invalidated`. The agent marks `Verified` when the verification plan confirms the assumption. Only a human can mark `Invalidated` (triggers impact analysis on dependent artifacts).

**Constraints**: consider technical (platforms, dependencies), business (budget, timeline, team size), and operational (hosting, compliance) categories.
Status lifecycle: `Active → Lifted`. Only a human can lift a constraint.

### Conflict resolution

A conflict exists when two or more requirements cannot both be satisfied as stated.

**Never resolve a conflict silently.** Always surface it before acting.

1. **Identify**: note conflicting requirement IDs, source stakeholders, influence levels, and why they are incompatible.
2. **Ask the user**: present what makes them incompatible, stakeholders and influence levels, two or more resolution options, and a recommended option if one is clearly better.
3. **Wait for explicit approval** before modifying any file.
4. **Apply**: update affected requirement files and index rows. Update dependent user stories or goals if affected. Record a design decision if the resolution imposes a recurring constraint.
5. **Verify**: no artifacts remain in a conflicting state after resolution.

### Assumption invalidation

When an assumption is found to be wrong or no longer holds:

1. **Identify impact**: list all artifacts (requirements, user stories, design decisions) that depend on the invalidated assumption.
2. **Ask the user**: present the invalidated assumption, the affected artifacts, and proposed adjustments or alternatives.
3. **Wait for explicit approval** before modifying any file.
4. **Apply**: change the assumption's Status to `Invalidated`. Update or flag all dependent artifacts as directed.
5. **Verify**: no artifacts remain based on the invalidated assumption without acknowledgment.

### Artifact deprecation

When an artifact (goal, user story, requirement) is no longer relevant:

1. Propose deprecation to the user with rationale and downstream impact.
2. Wait for explicit approval.
3. Change Status to `Deprecated` in the artifact file. Update its index row.
4. Check for dependent artifacts — flag any that reference the deprecated item.

---

## Linking to Other Phases

- Goals, user stories, constraints, assumptions, and requirements are referenced in design documents (`2-design/`)
- Requirements determine the development tasks in `3-code/tasks.md`; each task references the requirements it fulfills
- Acceptance criteria inform test cases (`3-code/`)

---

## Goals Index

| File | Priority | Status | Summary |
|------|----------|--------|---------|
| [GOAL-local-tts-synthesis](goals/GOAL-local-tts-synthesis.md) | Must-have | Approved | Convert text to speech entirely locally, no external API calls |
| [GOAL-browser-ui](goals/GOAL-browser-ui.md) | Must-have | Approved | Clean, intuitive browser-based interface for TTS conversion |
| [GOAL-easy-deployment](goals/GOAL-easy-deployment.md) | Should-have | Approved | Simple installation and operation with minimal configuration |
| [GOAL-audio-quality](goals/GOAL-audio-quality.md) | Should-have | Approved | Natural-sounding speech output with multiple voice options |
| [GOAL-audiobook-creation](goals/GOAL-audiobook-creation.md) | Must-have | Approved | Create complete audiobooks from text files (txt) |
| [GOAL-audiobook-library](goals/GOAL-audiobook-library.md) | Must-have | Approved | Browse, play, resume, and delete audiobooks from the web interface |
| [GOAL-backend-monitoring](goals/GOAL-backend-monitoring.md) | Should-have | Approved | Monitor backend processing jobs and resources from the UI |
| [GOAL-validate-local-ai-execution](goals/GOAL-validate-local-ai-execution.md) | Should-have | Approved | Validate local AI model execution via web interface; ensure reusability |
| [GOAL-huggingface-models](goals/GOAL-huggingface-models.md) | Must-have | Approved | Support open-weight HuggingFace models loaded on-demand |
| [GOAL-quick-tts-preview](goals/GOAL-quick-tts-preview.md) | Should-have | Approved | Quick TTS from direct text input for voice/model previews |
| [GOAL-text-normalization](goals/GOAL-text-normalization.md) | Must-have | Approved | Normalize/clean input text into TTS-ready form before synthesis |

---

## User Stories Index

| File | Role | Priority | Status | Summary |
|------|------|----------|--------|---------|
| [US-create-audiobook](user-stories/US-create-audiobook.md) | STK-end-user | Must-have | Approved | Upload .txt file and convert it into an audiobook locally |
| [US-browse-audiobook-library](user-stories/US-browse-audiobook-library.md) | STK-end-user | Must-have | Approved | Browse library of generated audiobooks |
| [US-play-audiobook](user-stories/US-play-audiobook.md) | STK-end-user | Must-have | Approved | Play audiobook from library with resume support |
| [US-download-audiobook](user-stories/US-download-audiobook.md) | STK-end-user | Should-have | Approved | Download audiobook files from the library |
| [US-delete-audiobook](user-stories/US-delete-audiobook.md) | STK-end-user | Must-have | Approved | Delete audiobooks to free storage space |
| [US-select-voice](user-stories/US-select-voice.md) | STK-end-user | Should-have | Approved | Select voice and output language before generating an audiobook |
| [US-select-tts-model](user-stories/US-select-tts-model.md) | STK-end-user | Must-have | Approved | Browse and select a HuggingFace TTS model to use |
| [US-monitor-jobs](user-stories/US-monitor-jobs.md) | STK-self-hoster | Should-have | Approved | View status of TTS jobs and system resource usage |
| [US-deploy-app](user-stories/US-deploy-app.md) | STK-self-hoster | Should-have | Approved | Install and run the app with minimal commands and configuration |
| [US-evaluate-local-ai](user-stories/US-evaluate-local-ai.md) | STK-developer | Should-have | Approved | Run TTS end-to-end locally and review performance data |
| [US-manage-models](user-stories/US-manage-models.md) | STK-self-hoster | Should-have | Approved | View cached models and disk usage, delete unneeded models |
| [US-synthesize-text-input](user-stories/US-synthesize-text-input.md) | STK-end-user | Should-have | Approved | Type or paste text and hear ephemeral TTS preview |
| [US-clean-text-for-tts](user-stories/US-clean-text-for-tts.md) | STK-end-user | Must-have | Approved | Automatic text cleaning/normalization before synthesis |
| [US-extensible-text-preprocessing](user-stories/US-extensible-text-preprocessing.md) | STK-developer | Should-have | Approved | Modular, language- and model-aware preprocessing pipeline |

---

## Requirements Index

| File | Type | Priority | Status | Summary |
|------|------|----------|--------|---------|
| [REQ-F-upload-text-file](requirements/REQ-F-upload-text-file.md) | Functional | Must-have | Approved | Accept .txt file uploads (UTF-8, ≤ 2 MB) via browser UI |
| [REQ-F-synthesize-audiobook](requirements/REQ-F-synthesize-audiobook.md) | Functional | Must-have | Approved | Convert full text to MP3 locally on GPU; no external calls |
| [REQ-F-chapter-split-output](requirements/REQ-F-chapter-split-output.md) | Functional | Must-have | Approved | Produce one MP3 per chapter; single file if no chapters detected |
| [REQ-F-synthesis-progress](requirements/REQ-F-synthesis-progress.md) | Functional | Must-have | Approved | Show job status and progress indicator during synthesis |
| [REQ-F-disk-space-preflight](requirements/REQ-F-disk-space-preflight.md) | Functional | Must-have | Approved | Check disk space before synthesis; block with error if insufficient |
| [REQ-F-library-listing](requirements/REQ-F-library-listing.md) | Functional | Must-have | Approved | Display list of audiobooks with title, creation date, chapter count |
| [REQ-F-audiobook-playback](requirements/REQ-F-audiobook-playback.md) | Functional | Must-have | Approved | Play audiobook in browser with chapter navigation |
| [REQ-F-playback-resume](requirements/REQ-F-playback-resume.md) | Functional | Must-have | Approved | Two-level playback bookmarks: audiobook-level (last chapter) and per-chapter (timestamp) |
| [REQ-F-delete-audiobook](requirements/REQ-F-delete-audiobook.md) | Functional | Must-have | Approved | Delete audiobook and audio files after user confirmation |
| [REQ-F-model-listing](requirements/REQ-F-model-listing.md) | Functional | Must-have | Approved | List compatible HuggingFace TTS models with cache status |
| [REQ-F-model-download](requirements/REQ-F-model-download.md) | Functional | Must-have | Approved | Download, cache, and load models with progress and disk check |
| [REQ-F-download-audiobook](requirements/REQ-F-download-audiobook.md) | Functional | Should-have | Approved | Download audiobook audio files in MP3 format |
| [REQ-F-voice-language-selection](requirements/REQ-F-voice-language-selection.md) | Functional | Should-have | Approved | Select voice and language before synthesis; sensible defaults |
| [REQ-F-job-monitoring](requirements/REQ-F-job-monitoring.md) | Functional | Should-have | Approved | Display TTS job status, progress, and error details |
| [REQ-F-resource-monitoring](requirements/REQ-F-resource-monitoring.md) | Functional | Should-have | Approved | Display CPU, memory, GPU usage and loaded model info |
| [REQ-USA-simple-setup](requirements/REQ-USA-simple-setup.md) | Usability | Should-have | Approved | Run in ≤ 5 commands, no config editing, shows URL on startup |
| [REQ-F-performance-logging](requirements/REQ-F-performance-logging.md) | Functional | Should-have | Approved | Record synthesis performance metrics per run |
| [REQ-MNT-modular-ai-layer](requirements/REQ-MNT-modular-ai-layer.md) | Maintainability | Should-have | Approved | AI layer with clear interfaces; extractable as standalone |
| [REQ-F-model-cache-view](requirements/REQ-F-model-cache-view.md) | Functional | Should-have | Approved | Display cached models with name and disk size |
| [REQ-F-model-delete](requirements/REQ-F-model-delete.md) | Functional | Should-have | Approved | Delete cached models; prevent deletion of loaded model |
| [REQ-F-text-preview](requirements/REQ-F-text-preview.md) | Functional | Should-have | Approved | Ephemeral TTS preview from text input field |
| [REQ-F-gpu-validation](requirements/REQ-F-gpu-validation.md) | Functional | Must-have | Approved | Verify NVIDIA GPU/CUDA on startup; check VRAM before model load |
| [REQ-PORT-linux-windows](requirements/REQ-PORT-linux-windows.md) | Portability | Must-have | Approved | Run on Linux and Windows without platform-specific workarounds |
| [REQ-COMP-foss-only](requirements/REQ-COMP-foss-only.md) | Compliance | Must-have | Approved | All dependencies free and open-source; no paid components |
| [REQ-PERF-synthesis-latency](requirements/REQ-PERF-synthesis-latency.md) | Performance | Should-have | Approved | Preview ≤ 30 s for 500 chars; audiobook RTF ≤ 3.0 on min-spec GPU |
| [REQ-F-default-voice-quality](requirements/REQ-F-default-voice-quality.md) | Functional | Should-have | Approved | Pre-tested default voice in Italian; ≥ 95% intelligibility |
| [REQ-PORT-browser-compat](requirements/REQ-PORT-browser-compat.md) | Portability | Should-have | Approved | Core workflows work on Chrome, Firefox, Edge desktop |
| [REQ-SEC-localhost-binding](requirements/REQ-SEC-localhost-binding.md) | Security | Must-have | Approved | Web server binds to localhost by default; not network-accessible |
| [REQ-F-text-numeric-symbolic-verbalization](requirements/REQ-F-text-numeric-symbolic-verbalization.md) | Functional | Must-have | Approved | Verbalize numbers, dates, percentages, currency, and symbols (language-aware) |
| [REQ-F-text-unicode-sanitization](requirements/REQ-F-text-unicode-sanitization.md) | Functional | Must-have | Approved | Sanitize invisible/disallowed Unicode, spacing, dashes, quotes, emoji |
| [REQ-F-text-layout-repair](requirements/REQ-F-text-layout-repair.md) | Functional | Must-have | Approved | Repair PDF line breaks/hyphenation, strip page numbers, reflow sentences |
| [REQ-F-abbreviation-expansion](requirements/REQ-F-abbreviation-expansion.md) | Functional | Should-have | Approved | Verbalize abbreviations/acronyms; optional domain dictionary |
| [REQ-MNT-preprocessing-pipeline](requirements/REQ-MNT-preprocessing-pipeline.md) | Maintainability | Should-have | Approved | Modular preprocessing pipeline configurable per language and per model |
| [REQ-PERF-preprocessing-overhead](requirements/REQ-PERF-preprocessing-overhead.md) | Performance | Should-have | Approved | Bound preprocessing time (≤10 s for 2 MB; ≤1 s for preview); no regression of synthesis latency |
| [REQ-USA-normalized-text-review](requirements/REQ-USA-normalized-text-review.md) | Usability | Should-have | Approved | Let user review normalized text and confirm before audio generation |

---

## Assumptions Index

| File | Category | Status | Risk | Summary |
|------|----------|--------|------|---------|
| [ASM-user-has-nvidia-gpu](assumptions/ASM-user-has-nvidia-gpu.md) | Environment | Verified | High | Users have an NVIDIA GPU with at least 4 GB VRAM |
| [ASM-huggingface-models-available](assumptions/ASM-huggingface-models-available.md) | Technology | Verified | High | Suitable open-weight TTS models exist on HuggingFace |
| [ASM-internet-for-model-download](assumptions/ASM-internet-for-model-download.md) | Environment | Verified | Low | Internet available for initial model download; synthesis is offline |
| [ASM-text-file-format](assumptions/ASM-text-file-format.md) | User | Verified | Medium | Users upload UTF-8 .txt files up to ~2 MB |
| [ASM-browser-mp3-playback](assumptions/ASM-browser-mp3-playback.md) | Technology | Verified | Low | Target browsers can natively play MP3 audio |
| [ASM-input-text-quality-varies](assumptions/ASM-input-text-quality-varies.md) | User | Verified | Medium | Real-world inputs (esp. PDF→txt) contain artifacts needing cleaning |

---

## Constraints Index

| File | Category | Status | Summary |
|------|----------|--------|---------|
| [CON-gpu-inference](constraints/CON-gpu-inference.md) | Technical | Active | All TTS inference must run on a dedicated GPU |
| [CON-nvidia-gpu](constraints/CON-nvidia-gpu.md) | Technical | Active | Only NVIDIA GPUs (CUDA) supported |
| [CON-cross-platform](constraints/CON-cross-platform.md) | Technical | Active | Must run on Linux and Windows; macOS out of scope |
| [CON-single-user](constraints/CON-single-user.md) | Operational | Active | Single-user deployment only |
| [CON-solo-developer](constraints/CON-solo-developer.md) | Business | Active | Solo developer; favor simplicity and low maintenance |
| [CON-zero-budget](constraints/CON-zero-budget.md) | Business | Active | No paid services, APIs, or libraries; all components free and open-source |
