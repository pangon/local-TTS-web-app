# ASM-browser-mp3-playback: Browser MP3 Playback Support

**Category**: Technology

**Status**: Verified

**Risk if wrong**: Low — MP3 playback is universally supported in modern browsers (Chrome, Firefox, Edge); risk is negligible

## Statement

Target browsers (Chrome, Firefox, Edge) can natively play MP3 audio files via the HTML5 `<audio>` element without additional plugins or codecs.

## Rationale

MP3 decoding has been supported in all major browsers for years and is the most widely compatible audio format on the web. The project targets modern desktop browsers only (see GOAL-browser-ui).

## Verification

Verified 2026-03-11 via MDN and caniuse.com. Chrome supports MP3 since v3 (2009), Firefox built-in since v71 (2019), Edge since v12 (2015). MP3 patents expired (US: 2017, EU: 2012). All target browsers decode MP3 natively without plugins. No fallback format needed.

## Related Artifacts

- [GOAL-browser-ui](../goals/GOAL-browser-ui.md), [GOAL-audiobook-creation](../goals/GOAL-audiobook-creation.md), [GOAL-quick-tts-preview](../goals/GOAL-quick-tts-preview.md)
