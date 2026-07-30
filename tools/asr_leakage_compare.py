"""Pure helpers for comparing ASR output with an SRT reference."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence


_TIMESTAMP_LINE = re.compile(
    r"^\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*"
    r"\d{1,2}:\d{2}:\d{2}[,.]\d{3}(?:\s+.*)?$"
)


@dataclass(frozen=True)
class Alignment:
    reference_count: int
    hypothesis_count: int
    deletions: list[str]
    insertions: list[str]
    substitutions: list[tuple[str, str]]

    @property
    def wer(self) -> float:
        """Return the word error rate relative to the reference length."""
        edits = len(self.deletions) + len(self.insertions) + len(self.substitutions)
        return edits / max(self.reference_count, 1)


@dataclass(frozen=True)
class ReviewDecision:
    """Classify local ASR differences and any available cloud review."""

    status: str
    reason: str
    review_required: bool
    confirmed_deletions: list[str]


def extract_srt_text(path: Path) -> str:
    """Return subtitle payload text, discarding SRT indices and timestamps."""
    text_lines: list[str] = []
    for block in re.split(r"\r?\n\s*\r?\n", path.read_text(encoding="utf-8-sig").strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and lines[0].isdigit():
            lines.pop(0)
        text_lines.extend(line for line in lines if not _TIMESTAMP_LINE.match(line))
    return " ".join(text_lines)


def language_root(language: str) -> str:
    """Return the primary language subtag from a Whisper/BCP-47 code."""
    return re.split(r"[-_]", language.casefold(), maxsplit=1)[0]


def normalize_tokens(text: str, language: str) -> list[str]:
    """Case-fold text and extract Unicode word tokens without ASCII conversion."""
    normalized = text.casefold()
    if language_root(language) in {"zh", "ja", "ko"}:
        return [character for character in normalized if character.isalnum()]
    return re.findall(r"\w+", normalized, flags=re.UNICODE)


def align_tokens(reference: Sequence[str], hypothesis: Sequence[str]) -> Alignment:
    """Align token sequences, preserving explicit deletion and insertion evidence.

    Dynamic-programming scores are ``(edit_count, substitution_count)``. This
    preserves the minimum WER while resolving equal-cost paths in favor of an
    insertion/deletion pair over substitutions when it identifies an omitted
    token more accurately.
    """
    reference = list(reference)
    hypothesis = list(hypothesis)
    rows = len(reference) + 1
    columns = len(hypothesis) + 1
    scores: list[list[tuple[int, int]]] = [[(0, 0)] * columns for _ in range(rows)]
    parents: list[list[str | None]] = [[None] * columns for _ in range(rows)]

    for index in range(1, rows):
        scores[index][0] = (index, 0)
        parents[index][0] = "deletion"
    for index in range(1, columns):
        scores[0][index] = (index, 0)
        parents[0][index] = "insertion"

    for ref_index in range(1, rows):
        for hyp_index in range(1, columns):
            if reference[ref_index - 1] == hypothesis[hyp_index - 1]:
                scores[ref_index][hyp_index] = scores[ref_index - 1][hyp_index - 1]
                parents[ref_index][hyp_index] = "match"
                continue

            deletion = (
                scores[ref_index - 1][hyp_index][0] + 1,
                scores[ref_index - 1][hyp_index][1],
                "deletion",
            )
            insertion = (
                scores[ref_index][hyp_index - 1][0] + 1,
                scores[ref_index][hyp_index - 1][1],
                "insertion",
            )
            substitution = (
                scores[ref_index - 1][hyp_index - 1][0] + 1,
                scores[ref_index - 1][hyp_index - 1][1] + 1,
                "substitution",
            )
            best = min((deletion, insertion, substitution), key=lambda item: item[:2])
            scores[ref_index][hyp_index] = best[:2]
            parents[ref_index][hyp_index] = best[2]

    deletions: list[str] = []
    insertions: list[str] = []
    substitutions: list[tuple[str, str]] = []
    ref_index = len(reference)
    hyp_index = len(hypothesis)
    while ref_index or hyp_index:
        operation = parents[ref_index][hyp_index]
        if operation == "match":
            ref_index -= 1
            hyp_index -= 1
        elif operation == "deletion":
            deletions.append(reference[ref_index - 1])
            ref_index -= 1
        elif operation == "insertion":
            insertions.append(hypothesis[hyp_index - 1])
            hyp_index -= 1
        elif operation == "substitution":
            substitutions.append((reference[ref_index - 1], hypothesis[hyp_index - 1]))
            ref_index -= 1
            hyp_index -= 1
        else:
            raise RuntimeError("alignment has no parent operation")

    deletions.reverse()
    insertions.reverse()
    substitutions.reverse()
    return Alignment(
        reference_count=len(reference),
        hypothesis_count=len(hypothesis),
        deletions=deletions,
        insertions=insertions,
        substitutions=substitutions,
    )


def classify_comparison(
    *,
    language: str,
    local_wer: float,
    local_deletion_rate: float,
    openai_fallback: bool,
    local_deletions: Sequence[str] = (),
    cloud_deletions: Sequence[str] | None = None,
    wer_threshold: float = 0.05,
    deletion_threshold: float = 0.02,
) -> ReviewDecision:
    """Return the review state without treating a single ASR as TTS evidence."""
    if language_root(language) != "en":
        reason = "non_english"
    elif local_wer > wer_threshold:
        reason = "local_wer_exceeded"
    elif local_deletion_rate > deletion_threshold:
        reason = "local_deletion_rate_exceeded"
    else:
        return ReviewDecision(
            status="local_pass",
            reason="local_quality_within_thresholds",
            review_required=False,
            confirmed_deletions=[],
        )

    if not openai_fallback:
        return ReviewDecision(
            status="cloud_review_skipped",
            reason="openai_fallback_disabled",
            review_required=True,
            confirmed_deletions=[],
        )

    if cloud_deletions is None:
        return ReviewDecision(
            status="cloud_review_required",
            reason=reason,
            review_required=True,
            confirmed_deletions=[],
        )

    cloud_missing = set(cloud_deletions)
    confirmed = list(dict.fromkeys(token for token in local_deletions if token in cloud_missing))
    if confirmed:
        return ReviewDecision(
            status="confirmed_leakage",
            reason="local_and_cloud_agree",
            review_required=True,
            confirmed_deletions=confirmed,
        )

    return ReviewDecision(
        status="manual_review",
        reason="local_and_cloud_disagree",
        review_required=True,
        confirmed_deletions=[],
    )


def transcribe_local(
    audio_path: Path,
    language: str,
    local_model_path: Path | None = None,
) -> dict[str, Any]:
    """Transcribe one audio file using the locally cached Faster-Whisper model."""
    from faster_whisper import WhisperModel

    model_source = str(local_model_path) if local_model_path else "base"
    model = WhisperModel(
        model_source,
        device="cpu",
        compute_type="int8",
        local_files_only=local_model_path is not None,
    )
    segment_iterator, info = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
    )
    segments = [
        {"start": segment.start, "end": segment.end, "text": segment.text.strip()}
        for segment in segment_iterator
        if segment.text.strip()
    ]
    return {
        "text": " ".join(segment["text"] for segment in segments),
        "segments": segments,
        "detected_language": info.language,
        "duration": info.duration,
        "model": model_source,
    }


def transcribe_openai(
    audio_path: Path,
    language: str,
    *,
    post: Callable[..., Any] | None = None,
    timeout: int = 120,
) -> str:
    """Use OpenAI transcription without exposing the environment credential."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    if post is None:
        import requests

        post = requests.post

    with audio_path.open("rb") as audio_file:
        response = post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (audio_path.name, audio_file, "audio/mpeg")},
            data={"model": "gpt-4o-transcribe", "language": language},
            timeout=timeout,
        )
    response.raise_for_status()
    payload = response.json()
    text = payload.get("text") if isinstance(payload, Mapping) else None
    if not isinstance(text, str):
        raise RuntimeError("OpenAI transcription response did not contain text")
    return text


def _redact(value: Any, key: str = "") -> Any:
    normalized_key = key.casefold()
    sensitive = (
        "api_key",
        "authorization",
        "auth",
        "token",
        "signature",
        "signed_url",
    )
    if normalized_key.endswith("url") or any(part in normalized_key for part in sensitive):
        return "[redacted]"
    if isinstance(value, Mapping):
        return {str(item_key): _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def build_report(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-serializable report with credentials and URLs removed."""
    return _redact(dict(payload))


def format_srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def write_srt(path: Path, segments: Sequence[Mapping[str, Any]]) -> None:
    """Write transcribed segments in standard SRT format."""
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        lines.extend(
            (
                str(index),
                f"{format_srt_timestamp(float(segment['start']))} --> "
                f"{format_srt_timestamp(float(segment['end']))}",
                str(segment["text"]),
                "",
            )
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _alignment_report(alignment: Alignment) -> dict[str, Any]:
    return {
        "reference_count": alignment.reference_count,
        "hypothesis_count": alignment.hypothesis_count,
        "wer": alignment.wer,
        "deletion_rate": len(alignment.deletions) / max(alignment.reference_count, 1),
        "deletions": alignment.deletions,
        "insertions": alignment.insertions,
        "substitutions": alignment.substitutions,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare a returned audiobook MP3 with its reference SRT."
    )
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--reference-srt", type=Path, required=True)
    parser.add_argument("--language", required=True, help="BCP-47/Whisper language code, such as en or ru")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--openai-fallback", action="store_true")
    parser.add_argument("--local-model-path", type=Path)
    parser.add_argument("--wer-threshold", type=float, default=0.05)
    parser.add_argument("--deletion-threshold", type=float, default=0.02)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    reference_text = extract_srt_text(args.reference_srt)
    reference_tokens = normalize_tokens(reference_text, args.language)
    local_result = transcribe_local(args.audio, args.language, args.local_model_path)
    write_srt(args.output_dir / "local.srt", local_result["segments"])
    local_alignment = align_tokens(
        reference_tokens,
        normalize_tokens(local_result["text"], args.language),
    )
    local_deletion_rate = len(local_alignment.deletions) / max(local_alignment.reference_count, 1)
    decision = classify_comparison(
        language=args.language,
        local_wer=local_alignment.wer,
        local_deletion_rate=local_deletion_rate,
        openai_fallback=args.openai_fallback,
        local_deletions=local_alignment.deletions,
        wer_threshold=args.wer_threshold,
        deletion_threshold=args.deletion_threshold,
    )
    cloud_alignment: Alignment | None = None

    if decision.status == "cloud_review_required":
        try:
            cloud_text = transcribe_openai(args.audio, args.language)
        except ValueError:
            decision = ReviewDecision(
                status="cloud_review_skipped",
                reason="openai_api_key_missing",
                review_required=True,
                confirmed_deletions=[],
            )
        except Exception:
            decision = ReviewDecision(
                status="cloud_review_skipped",
                reason="openai_request_failed",
                review_required=True,
                confirmed_deletions=[],
            )
        else:
            (args.output_dir / "openai.txt").write_text(cloud_text, encoding="utf-8")
            cloud_alignment = align_tokens(
                reference_tokens, normalize_tokens(cloud_text, args.language)
            )
            decision = classify_comparison(
                language=args.language,
                local_wer=local_alignment.wer,
                local_deletion_rate=local_deletion_rate,
                openai_fallback=True,
                local_deletions=local_alignment.deletions,
                cloud_deletions=cloud_alignment.deletions,
                wer_threshold=args.wer_threshold,
                deletion_threshold=args.deletion_threshold,
            )

    report = build_report(
        {
            "audio_filename": args.audio.name,
            "reference_srt_filename": args.reference_srt.name,
            "language": args.language,
            "local_backend": "faster-whisper",
            "local_model": local_result["model"],
            "local_alignment": _alignment_report(local_alignment),
            "cloud_backend": "openai/gpt-4o-transcribe" if cloud_alignment else None,
            "cloud_alignment": _alignment_report(cloud_alignment) if cloud_alignment else None,
            "decision": {
                "status": decision.status,
                "reason": decision.reason,
                "review_required": decision.review_required,
                "confirmed_deletions": decision.confirmed_deletions,
            },
        }
    )
    report_path = args.output_dir / "comparison.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
