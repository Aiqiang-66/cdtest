# ASR Leakage Fallback Design

## Goal

Prevent ASR recognition errors from being reported as TTS material leakage when comparing returned MP3 files with service-generated SRT files.

## Evidence

The local Faster-Whisper `base` model produced a 2.41% WER and 1.20% apparent deletion rate on a 120-second English material sample. The same method produced an 18.85% WER and 6.92% apparent deletion rate on a Russian sample. The local `large-v3` model cannot load on this CPU-only machine because of memory exhaustion.

## Design

The comparison command has two stages:

1. Faster-Whisper `base` transcribes every selected MP3 locally and writes a generated SRT.
2. The tool aligns the generated SRT with the reference SRT, calculates deletion, insertion, substitution, and WER/CER metrics, and identifies suspect time spans.
3. English results within the configured ASR-quality limits are accepted as the initial comparison outcome. Any non-English result, or an English result over the limits, is sent to OpenAI's transcription API for a second transcription.
4. A deletion is reported as a confirmed TTS leakage only when the OpenAI transcription also omits the aligned reference text. Results that differ between local and cloud ASR are marked `asr_disagreement` for manual review, not as leakage.

## Configuration and Security

- `OPENAI_API_KEY` is read only from the environment. It is never stored in output files or logs.
- OpenAI calls are opt-in through an explicit `--openai-fallback` flag.
- Reports retain only the backend name, model name, metrics, timestamps, and text snippets required for review. Signed COS URLs and authentication headers are excluded.

## Acceptance Criteria

- English and Russian samples produce a local SRT and structured comparison result.
- Russian automatically enters cloud review when enabled.
- A cloud-confirmed deletion is classified as `confirmed_leakage`.
- A disagreement between local and cloud ASR is classified as `manual_review`.
- With no API key or disabled fallback, the result remains usable and explicitly records why cloud review was skipped.

## Test Coverage

| Dimension | Status | Coverage |
| --- | --- | --- |
| functional | covered | Local comparison, confirmed leakage, and ASR disagreement classification. |
| api | covered | OpenAI request construction, response parsing, and missing-key handling. |
| database | not_applicable | The tool operates only on local media and report files. |
| security | covered | Environment-only API key access and redacted reporting. |
| performance | covered | Local-first processing; cloud calls limited to suspect/non-English files. |
| parameterized | covered | Language, thresholds, fallback enablement, and backend selection. |
| integration | covered | MP3, reference SRT, local ASR, OpenAI ASR, and report pipeline. |
