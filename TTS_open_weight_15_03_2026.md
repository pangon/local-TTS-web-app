# The 12 Best Open-Weight TTS Models for Local Use (2026)

**The open-weight TTS model landscape has reached a tipping point: several open-source models now compete on par with commercial services like ElevenLabs.** This report profiles the best candidates for a project requiring local GPU deployment, multilingual support (including Italian), and high audio quality. Models are ranked by overall recommendation strength, balancing quality, Italian support, licensing, and deployment practicality.

---

## Quick Overview

| # | Model | Developer | Parameters | License | Italian | Voice Cloning | VRAM | Speed |
|---|-------|-----------|------------|---------|---------|---------------|------|-------|
| 1 | **Chatterbox** | Resemble AI | 350M–500M | MIT | Yes (23 languages) | Yes Zero-shot | ~2–6 GB | 6x real-time |
| 2 | **Qwen3-TTS** | Alibaba/Qwen | 0.6B–1.7B | Apache 2.0 | Yes (10 languages) | Yes Zero-shot (3s) | ~2.5–4.5 GB | 97ms latency |
| 3 | **CosyVoice 3** | Alibaba/FunAudioLLM | 0.5B | Apache 2.0 | Yes (9 languages) | Yes Zero-shot | ~3–4 GB | 150ms latency |
| 4 | **Kokoro v1.0** | Hexgrad | 82M | Apache 2.0 | Yes (2 voices) | No | Nearly zero | **210x real-time** |
| 5 | **Higgs Audio V2** | Boson AI | 3B (+ 1B v2.5) | Apache 2.0 | Partial (32 languages, variable quality) | Yes Zero-shot | ~6–16 GB | 1.3x RTF on 4090 |
| 6 | **XTTS-v2** | Coqui/Idiap | ~1.1B | MPL-2.0 / CPML | Yes (17 languages) | Yes Zero-shot (6s) | ~4–6 GB | Streaming <200ms |
| 7 | **Fish Speech v1.5** | Fish Audio | ~500M | CC-BY-NC-SA | Yes (<10K hours) | Yes Zero-shot | ~4 GB | 1:5–1:15 RTF |
| 8 | **Orpheus TTS** | Canopy Labs | 150M–3B | Apache 2.0 | Yes (preview) | Yes Zero-shot | ~6–16 GB | ~200ms streaming |
| 9 | **F5-TTS** | SWivid | 335M | MIT / CC-BY-NC* | Partial Cross-lingual | Yes Zero-shot | ~2–3 GB | RTF ~0.15 |
| 10 | **Parler-TTS** | Hugging Face | 880M–2.3B | Apache 2.0 | Yes (8 languages) | No | ~4–10 GB | Moderate |
| 11 | **Zonos** | Zyphra | 1.6B | Apache 2.0 | Partial Limited | Yes Zero-shot | ~6–8 GB | 2x RTF on 4090 |
| 12 | **Dia** | Nari Labs | 1.6B | Apache 2.0 | No English only | Yes Zero-shot | ~8–10 GB | Real-time |

*\*F5-TTS: code is MIT; model weights are CC-BY-NC due to training data.*

---

## 1. Chatterbox — The Open-Source Champion

Resemble AI released **Chatterbox** in three variants: the original English model (500M backbone, trained on 500K hours), Chatterbox Multilingual (23 languages including Italian, released September 2025), and Chatterbox Turbo (350M parameters, optimized for speed at 6x real-time). In blind evaluations, it achieved a 63.75% preference rate over ElevenLabs — the first open-source model to convincingly beat a commercial leader. It ranks #16 on the TTS Arena V2 leaderboard, the highest among all open models.

The **MIT license** makes it the most permissive high-quality option. Features include: zero-shot voice cloning from a few seconds of reference audio, an emotion exaggeration slider (unique among open models), paralinguistic tags like `[laugh]` and `[cough]` in the Turbo variant, and built-in PerTh neural watermarking. Italian is one of 23 fully supported languages. VRAM requirements are modest: approximately **2–4 GB for Turbo, 4–6 GB for the full model**. Over 21,000 GitHub stars with very active maintenance.

- **GitHub:** github.com/resemble-ai/chatterbox
- **HuggingFace:** ResembleAI/chatterbox

---

## 2. Qwen3-TTS — The Most Feature-Complete for Functionality and Languages

Released in January 2026 by Alibaba's Qwen team, **Qwen3-TTS** is a family of 6 models (0.6B and 1.7B variants) covering three usage modes: **CustomVoice** (9 preset voices with style control via instructions), **VoiceDesign** (creates entirely new voices from text descriptions), and **Base** (zero-shot voice cloning from just 3 seconds of audio). It is trained on over 5 million hours of voice data in 10 languages.

It natively supports **Italian, English, Chinese, Japanese, Korean, German, French, Russian, Portuguese, and Spanish** — one of the broadest language coverages available. The dual-track LM architecture enables an end-to-end latency of just **97ms** for the first audio packet, making it ideal for real-time interactive applications. In benchmarks, it achieved a mean WER of 1.835% across 10 languages with 0.789 voice similarity, surpassing MiniMax and ElevenLabs.

The 1.7B model requires approximately **4.5 GB**, the 0.6B about **2.5 GB**. **Apache 2.0** license on everything (code and weights), fully commercial. Integrates FlashAttention 2, vLLM for serving, and supports both streaming and batch generation. Rapidly growing ecosystem with ComfyUI integration and very active community support.

- **GitHub:** github.com/QwenLM/Qwen3-TTS
- **HuggingFace:** Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice (and variants)

---

## 3. CosyVoice 3 — Extreme Efficiency with 0.5B Parameters

Fun-CosyVoice 3.0, released in December 2025 by Alibaba's FunAudioLLM team, is the third iteration of a series that has progressively improved quality and speed. With only **0.5B parameters**, it surpasses models three times larger on key metrics: a CER (Character Error Rate) of 0.81% in Chinese and voice similarity of 78.0% — a figure close to real human recording levels (approximately 75.5%).

It covers **9 languages including Italian**, plus 18+ Chinese dialects. Zero-shot voice cloning also works cross-lingually (clone a voice in English, generate in Italian). Unique features include: **Pronunciation Inpainting** for phoneme-level pronunciation correction (useful for proper nouns and technical terms), and instruction-based control of speed, emotion, and volume. First packet latency of just **150ms** in streaming mode.

**Apache 2.0** license. Estimated VRAM **3–4 GB**. Up to 4x acceleration with TensorRT-LLM. Fully open-source pipeline (training, inference, deployment).

- **GitHub:** github.com/FunAudioLLM/CosyVoice
- **HuggingFace:** FunAudioLLM/Fun-CosyVoice3-0.5B-2512

---

## 4. Kokoro — 82 Million Parameters Competing with the Giants

With only **82 million parameters** and a model file of approximately 350 MB, Kokoro is an efficiency phenomenon. It ranked #1 on HuggingFace's TTS Spaces Arena for single-speaker quality and #17 on the full TTS Arena V2. It runs at **210x real-time on GPU and 3–11x real-time on CPU only** — by far the fastest high-quality option. One user generated a six-hour audiobook in four minutes.

Based on the StyleTTS 2 / ISTFTNet architecture (decoder-only, no diffusion), Kokoro supports **9 languages with 54 total voices**, including two Italian voices (if_sara and im_nicola). The developer warns that non-English support may be weaker due to limited G2P and training data, so Italian quality may not match English. The **Apache 2.0 license** covers everything without restrictions. It does not support voice cloning — it uses a curated voice library with blending capabilities. For projects requiring ultra-low latency or edge deployment, nothing comes close.

- **GitHub:** github.com/hexgrad/kokoro
- **HuggingFace:** hexgrad/Kokoro-82M

---

## 5. Higgs Audio V2 — The Most Expressive Audio Foundation Model

Released in July 2025 by Boson AI, Higgs Audio V2 is not just a TTS model but a true **audio foundation model** trained on over 10 million hours of audio data. In EmergentTTS-Eval, it achieves win-rates of 75.7% and 55.7% against GPT-4o-mini-TTS in the "Emotions" and "Questions" categories — results that place it among the most expressive overall.

With **3B parameters** (or 1B in the condensed v2.5 version), the model demonstrates rarely seen capabilities: multi-speaker generation in multiple languages, automatic prosody adaptation in narration, melodic humming with a cloned voice, and simultaneous voice and background music generation. It supports **32 languages in pre-training**, but quality is best for English, Chinese, and Spanish; Italian is present but with variable quality.

**Apache 2.0** license. The 3B model requires at least an **RTX 4090** for efficient inference (~1.3x real-time). The v2.5 (1B) is lighter. Audio at 24kHz (superior to v1's 16kHz). Zero-shot voice cloning from 3-10 seconds of reference.

- **GitHub:** github.com/boson-ai/higgs-audio
- **HuggingFace:** bosonai/higgs-audio-v2-generation-3B-base

---

## 6. XTTS-v2 — The Battle-Tested Multilingual Veteran

Despite Coqui AI's closure in 2023, **XTTS-v2 remains the most battle-tested multilingual model** thanks to active maintenance by the Idiap Research Institute. It supports **17 languages natively, including Italian** as a first-class language, and allows zero-shot voice cloning from just 6 seconds with cross-lingual transfer (clone in English, generate in Italian). Streaming runs under 200ms latency.

The architecture is based on GPT-2, so absolute quality has been surpassed by 2025 models, but for a proven, mature system with strong Italian support, it remains hard to beat. The license is split: framework under **MPL-2.0**, model weights under **Coqui Public Model License (CPML)** which allows commercial use with some restrictions. VRAM approximately **4–6 GB**.

- **GitHub:** github.com/idiap/coqui-ai-TTS
- **HuggingFace:** coqui/XTTS-v2

---

## 7. Fish Speech v1.5 — The Multilingual Quality Frontier

Fish Audio uses a **dual-autoregressive architecture without G2P conversion** — the LLM understands text directly — paired with a Firefly-GAN vocoder. Version 1.5 supports **13+ languages including Italian** (with less than 10K hours of Italian data versus 300K+ for English and Chinese). The most recent S2 variant achieves the **lowest WER** among all evaluated models, including closed-source ones.

The open v1.5 model fits in approximately **4 GB of VRAM** with zero-shot voice cloning from 10–30 seconds and ~150ms first-packet latency. The critical limitation: weights are licensed under **CC-BY-NC-SA-4.0** (non-commercial). The code is BSD-3-Clause. For commercial use, the larger S2 model must be licensed separately. For research or non-commercial use, Fish Speech v1.5 represents one of the highest absolute quality levels available.

- **GitHub:** github.com/fishaudio/fish-speech
- **HuggingFace:** fishaudio/fish-speech-1.5

---

## 8. Orpheus TTS — The Emotionally Expressive Voice on a Llama Backbone

Canopy Labs built Orpheus on **Meta Llama-3B**, creating a speech-LLM trained on 100K+ hours of English audio plus billions of text tokens. The result is a model with **emergent emotional speech capabilities** controllable via inline tags: `<laugh>`, `<sigh>`, `<gasp>`, `<chuckle>`, `<cough>`, and more. Streaming can reach latencies of **25–50ms**.

The model is available in **four sizes (3B, 1B, 400M, 150M)**, all under Apache 2.0. Italian is available through a multilingual preview (April 2025) as a separate download, with quality labeled as experimental. Quantized GGUF versions work with llama.cpp. The 3B requires approximately **12–16 GB VRAM** in FP16, ~6 GB with quantization.

- **GitHub:** github.com/canopyai/Orpheus-TTS
- **HuggingFace:** canopylabs/orpheus-3b-0.1-ft

---

## 9. F5-TTS — Flow Matching for Elegant Voice Cloning

F5-TTS is **completely non-autoregressive**, using flow matching with a Diffusion Transformer. No duration model, no text encoder, no phoneme alignment — text is simply padded with filler tokens. The result is an inference RTF of approximately **0.15** (about 7x real-time) with only **2–3 GB of VRAM**. Over 14,100 GitHub stars.

Zero-shot voice cloning has been called "state-of-the-art" by independent reviewers. The model also supports speech inpainting. Primary languages are **English and Chinese** (trained on the 100K-hour Emilia dataset), with cross-lingual voice cloning possible for other languages — but Italian is not a primary language and results can be inconsistent. Weight license is **CC-BY-NC**, code is MIT.

- **GitHub:** github.com/SWivid/F5-TTS
- **HuggingFace:** SWivid/F5-TTS

---

## 10. Parler-TTS — Describe the Voice You Want in Natural Language

Parler-TTS introduces a unique paradigm: instead of selecting a voice preset, you **describe the voice in natural language** — "A female speaker with a warm, slightly low voice, speaking expressively in a quiet room." The model generates matching speech. The Multilingual v1.1 variant supports **8 European languages including Italian**.

Developed by Hugging Face with an **Apache 2.0 license**, all training data, preprocessing code, and weights are public — a rarity even among "open" models. The Mini variant (880M–938M) requires approximately **4 GB of VRAM**, the Large (2.3B) requires 8–10 GB. It does not support traditional voice cloning, but natural language control offers unique flexibility.

- **GitHub:** github.com/huggingface/parler-tts
- **HuggingFace:** parler-tts/parler-tts-mini-multilingual-v1.1

---

## 11. Zonos — The Most Granular Control Over Emotions and Prosody

Zonos by Zyphra stands out for its **fine-grained control over emotions, speed, pitch, and audio quality** — adjustable parameters that most other models do not offer. It features happiness, anger, sadness, and fear as controllable emotions, plus a hybrid variant that is the **first open-source SSM (Mamba2) model for TTS**. Voice cloning works from 5–30 seconds of reference, and output is native at 44kHz (superior to the 24kHz of most competitors).

The 1.6B model runs at approximately **2x real-time on RTX 4090** with ~6–8 GB of VRAM. Italian is not in the primary language set (English, Japanese, Chinese, French, Spanish, German), but some cross-lingual capability exists. **Apache 2.0** license.

- **GitHub:** github.com/Zyphra/Zonos
- **HuggingFace:** Zyphra/Zonos-v0.1-transformer

---

## 12. Dia — Specialized for Multi-Speaker Dialogues

Dia by Nari Labs is a **1.6B model specialized for dialogue generation**. Where other models synthesize one speaker at a time, Dia produces multi-speaker conversations in a single pass using `[S1]`/`[S2]` tags, complete with non-verbal vocalizations — laughter, coughs, sighs. Ideal for audiobooks, podcasts, NPC dialogues in games.

The main limitation is that it is **English only** — no Italian support for now. **Apache 2.0** license, approximately **8–10 GB of VRAM**, about 40 tokens/second on A4000. If the Italian requirement is flexible for certain use cases, Dia's dialogue capabilities are unmatched.

- **GitHub:** github.com/nari-labs/dia
- **HuggingFace:** nari-labs/Dia-1.6B-0626

---

## Honorable Mentions to Watch

- **IndexTTS-2** (Bilibili, September 2025) — The first autoregressive model with precise synthesis duration control, excellent for video dubbing. Top-tier emotional expressiveness with control via reference audio, text description, or emotion vector. Limitation: Chinese and English only.
- **Sesame CSM** (Sesame AI, Apache 2.0) — A 1B parameter conversational model that uses dialogue history to generate contextually appropriate speech. English only, but prosodic naturalness is extraordinary. ~4.5 GB VRAM.
- **Piper** — The reference for embedded/edge deployment. Runs on Raspberry Pi, 15–65 MB per voice, 30+ languages including Italian. Modest quality but unbeatable speed for low-resource devices.

---

## Italian Support Analysis

Italian support is the key differentiator for this project. Here is how the models stack up:

**Full and native Italian support:**
- **Chatterbox Multilingual** — Italian is one of 23 languages, with voice cloning. The overall strongest option.
- **Qwen3-TTS** — Native Italian among 10 languages, with voice cloning from 3 seconds, voice design, and streaming at 97ms. The richest feature set.
- **CosyVoice 3** — Italian among 9 languages, with cross-lingual voice cloning and pronunciation inpainting.
- **XTTS-v2** — First-class Italian among 17 languages. The most battle-tested over time.
- **Parler-TTS** — Italian among 8 European languages. Fully transparent training pipeline.

**Italian support present but limited:**
- **Kokoro** — Two Italian voices (if_sara, im_nicola), but the developer warns quality may be inferior to English.
- **Fish Speech v1.5** — Italian with <10K hours of training. Good quality but non-commercial license.
- **Orpheus** — Experimental multilingual preview.

**Italian support absent or very limited:**
- **Higgs Audio V2** — 32 languages in pre-training but best quality on English/Chinese/Spanish.
- **F5-TTS** — Cross-lingual only, inconsistent results.
- **Zonos** — Not in the primary set.
- **Dia** — English only.

---

## Licensing Notes

Licensing is the hidden constraint. Several high-quality models (Fish Speech, F5-TTS) have non-commercial licenses on weights despite open code. For commercial deployment, the options with Apache 2.0 or MIT licenses on both code AND weights are: **Chatterbox, Qwen3-TTS, CosyVoice 3, Kokoro, Higgs Audio V2, Orpheus, Dia, Parler-TTS, and Zonos**.

---

## Final Recommendation

For a project requiring Italian support on local GPU, the **recommended three-model stack** is:

1. **Chatterbox Multilingual** for the highest overall quality — MIT, 23 languages, voice cloning, emotions
2. **Qwen3-TTS** for the most complete feature set — voice cloning from 3s, voice design, streaming 97ms, 10 languages including Italian
3. **Kokoro** for paths where extreme speed is needed — 210x real-time, negligible VRAM

CosyVoice 3 is an excellent alternative to XTTS-v2 for those seeking a lightweight model (0.5B) with near state-of-the-art quality. Higgs Audio V2 deserves attention for anyone needing maximum emotional expressiveness, especially in English.
