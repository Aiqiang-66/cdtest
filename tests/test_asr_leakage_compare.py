import json

import tools.asr_leakage_compare as compare

from tools.asr_leakage_compare import (
    align_tokens,
    build_report,
    classify_comparison,
    extract_srt_text,
    normalize_tokens,
    transcribe_openai,
)


def test_extract_srt_text_ignores_indices_and_timestamps(tmp_path):
    source = tmp_path / "reference.srt"
    source.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nHello world.\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nAgain!\n",
        encoding="utf-8",
    )

    assert extract_srt_text(source) == "Hello world. Again!"


def test_align_tokens_reports_deletion_instead_of_substitution():
    result = align_tokens(
        normalize_tokens("alpha beta gamma", "en"),
        normalize_tokens("alpha gamma", "en"),
    )

    assert result.deletions == ["beta"]
    assert result.insertions == []
    assert result.substitutions == []


def test_normalize_tokens_uses_characters_for_unspaced_chinese_text():
    assert normalize_tokens("\u4f60\u597d\uff0c\u4e16\u754c", "zh") == ["\u4f60", "\u597d", "\u4e16", "\u754c"]


def test_non_english_result_requires_cloud_review():
    decision = classify_comparison(
        language="ru",
        local_wer=0.01,
        local_deletion_rate=0.0,
        openai_fallback=True,
    )

    assert decision.review_required is True
    assert decision.reason == "non_english"
    assert decision.status == "cloud_review_required"


def test_english_bcp47_variant_uses_local_thresholds():
    decision = classify_comparison(
        language="en-US",
        local_wer=0.01,
        local_deletion_rate=0.0,
        openai_fallback=True,
    )

    assert decision.status == "local_pass"


def test_cloud_disagreement_is_manual_review():
    result = classify_comparison(
        language="ru",
        local_wer=0.18,
        local_deletion_rate=0.06,
        openai_fallback=True,
        local_deletions=["missing"],
        cloud_deletions=[],
    )

    assert result.status == "manual_review"


def test_matching_local_and_cloud_deletions_confirm_leakage():
    result = classify_comparison(
        language="en",
        local_wer=0.08,
        local_deletion_rate=0.03,
        openai_fallback=True,
        local_deletions=["missing"],
        cloud_deletions=["missing"],
    )

    assert result.status == "confirmed_leakage"
    assert result.confirmed_deletions == ["missing"]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_openai_request_uses_environment_key_and_never_returns_it(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"test audio")
    captured = {}

    def fake_post(url, headers, files, data, timeout):
        captured.update(url=url, headers=headers, data=data)
        return FakeResponse({"text": "hello world"})

    assert transcribe_openai(audio, "en", post=fake_post) == "hello world"
    assert captured["url"] == "https://api.openai.com/v1/audio/transcriptions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["data"] == {"model": "gpt-4o-transcribe", "language": "en"}


def test_report_redacts_urls_and_keys():
    report = build_report(
        {
            "audio_url": "https://example.test/?signature=secret",
            "api_key": "secret",
            "nested": {"authorization": "Bearer secret"},
        }
    )

    assert "secret" not in json.dumps(report)


def test_main_writes_local_srt_and_skips_cloud_review_without_key(monkeypatch, tmp_path):
    audio = tmp_path / "audio.mp3"
    reference = tmp_path / "reference.srt"
    output_dir = tmp_path / "output"
    audio.write_bytes(b"test audio")
    reference.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nhello missing\n", encoding="utf-8"
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        compare,
        "transcribe_local",
        lambda *_: {
            "text": "hello",
            "segments": [{"start": 0.0, "end": 1.0, "text": "hello"}],
            "model": "test-model",
        },
    )

    assert compare.main(
        [
            "--audio",
            str(audio),
            "--reference-srt",
            str(reference),
            "--language",
            "ru",
            "--output-dir",
            str(output_dir),
            "--openai-fallback",
        ]
    ) == 0

    report = json.loads((output_dir / "comparison.json").read_text(encoding="utf-8"))
    assert (output_dir / "local.srt").exists()
    assert report["decision"]["status"] == "cloud_review_skipped"
    assert report["decision"]["reason"] == "openai_api_key_missing"
