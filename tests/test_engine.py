import asyncio

import pytest

from conftest import make_engine
from engine import DEFAULT_REVISION, EngineError, MAX_CHARS, split_text


def speak(engine, text="hello", voice=None, seed=1, temperature=0.8):
    return asyncio.run(engine.synthesize(text, voice, seed, temperature))


def collect(engine, text="One. Two. Three.", voice=None, seed=1, temperature=0.8):
    async def run():
        return [piece async for piece in engine.stream(text, voice, seed, temperature)]

    return asyncio.run(run())


def test_split_keeps_short_text_whole_and_packs_sentences_up_to_the_limit():
    assert split_text("Hello there.") == ["Hello there."]
    assert split_text("One. Two. Three.") == ["One. Two. Three."]
    sentences = ["A" * 100 + ".", "B" * 100 + ".", "C" * 10 + "."]
    assert split_text(" ".join(sentences)) == [sentences[0], sentences[1] + " " + sentences[2]]


def test_split_cuts_a_long_sentence_at_spaces_and_text_without_spaces_at_the_limit():
    words = " ".join(["word"] * 100)  # 499 characters, no punctuation
    pieces = split_text(words)
    assert all(len(piece) <= MAX_CHARS for piece in pieces) and " ".join(pieces) == words
    chinese = "我" * 400
    assert [len(piece) for piece in split_text(chinese)] == [150, 150, 100]


def test_split_does_not_cut_inside_numbers_and_splits_after_cjk_punctuation_without_spaces():
    assert split_text("Pi is 3.14 and it is 10:30 now.") == ["Pi is 3.14 and it is 10:30 now."]
    assert split_text("你好。我是机器人！") == ["你好。 我是机器人！"]  # short enough to be packed into one piece
    assert split_text("我" * 100 + "。" + "你" * 100) == ["我" * 100 + "。", "你" * 100]


def test_split_drops_text_with_nothing_to_say():
    assert split_text("...") == [] and split_text("   ") == [] and split_text("") == []


def test_the_model_loads_once_with_the_pinned_revision_and_speaks_without_a_reference():
    engine = make_engine()
    assert engine.voices == ["none"] and engine.default_voice == "none" and not engine.ready
    first = speak(engine)
    speak(engine, "again")
    assert first["voice"] == "none" and first["seconds"] == pytest.approx(0.1) and first["wav"][:4] == b"RIFF"
    assert engine.loads == [(DEFAULT_REVISION, "cuda", "bfloat16")] and engine.ready
    assert [call["texts"] for call in engine.made[0].calls] == [["hello"], ["again"]]
    assert engine.made[0].calls[0]["reference"] is None


def test_a_stored_voice_gives_the_model_its_clip_and_transcript():
    engine = make_engine(voices=["anna"])
    assert engine.voices == ["none", "anna"]
    assert speak(engine, voice="anna", seed=7, temperature=0.5)["voice"] == "anna"
    call = engine.made[0].calls[0]
    path, text = call["reference"]
    assert path.name == "anna.wav" and text == "Transcript of anna."
    assert call["seed"] == 7 and call["temperature"] == 0.5 and call["max_new_tokens"] == 1024


def test_an_unknown_voice_is_404():
    with pytest.raises(EngineError) as error:
        speak(make_engine(), voice="zz_nobody")
    assert error.value.status == 404


def test_long_text_is_spoken_piece_by_piece():
    engine = make_engine()
    text = " ".join(["word"] * 100)
    result = speak(engine, text)
    assert len(engine.made[0].calls[0]["texts"]) == 4 and result["seconds"] == pytest.approx(0.4)


def test_stream_gives_the_audio_piece_by_piece():
    engine = make_engine()
    pieces = collect(engine, text=" ".join(["word"] * 100))
    assert [rate for rate, _ in pieces] == [24000] * 4 and all(len(data) == 4800 for _, data in pieces)


def test_an_unpacked_stream_makes_one_piece_per_sentence():
    assert split_text("One. Two. Three.", pack=False) == ["One.", "Two.", "Three."]
    assert len(collect_unpacked(make_engine(), "One. Two. Three.")) == 3


def collect_unpacked(engine, text):
    async def run():
        return [piece async for piece in engine.stream(text, None, 1, 0.8, pack=False)]

    return asyncio.run(run())


def test_stream_refuses_an_unknown_voice_and_empty_text():
    with pytest.raises(EngineError) as unknown:
        collect(make_engine(), voice="zz_nobody")
    assert unknown.value.status == 404
    with pytest.raises(EngineError) as empty:
        collect(make_engine(), text="...")
    assert empty.value.status == 422


def test_closing_a_stream_early_frees_the_generation_slot():
    async def run():
        engine = make_engine()
        pieces = engine.stream(" ".join(["word"] * 100), None, 1, 0.8)
        await anext(pieces)
        await pieces.aclose()
        return await asyncio.wait_for(engine.synthesize("again", None, 1, 0.8), 2)

    assert asyncio.run(run())["seconds"] == pytest.approx(0.1)


def test_a_new_download_by_another_replica_drops_the_loaded_model(tmp_path):
    marker = tmp_path / "marker"
    one, two = make_engine(marker=marker), make_engine(marker=marker)
    speak(one)
    asyncio.run(two.unload())
    one.sync()
    assert not one.ready
    speak(one)
    assert len(one.loads) == 2


def test_the_revision_calls_use_the_model_and_revision():
    engine = make_engine(revision="abc", cached_sha=lambda model, rev: f"cached-{rev}", remote_sha=lambda model, rev: f"latest-{rev}")
    assert asyncio.run(engine.cached_sha()) == "cached-abc" and asyncio.run(engine.remote_sha()) == "latest-abc"


def test_the_thread_count_reaches_the_model_without_a_reload():
    engine = make_engine()
    speak(engine)
    engine.num_thread = 3
    speak(engine)
    assert engine.loads == [(DEFAULT_REVISION, "cuda", "bfloat16")] and engine.made[0].calls[1]["threads"] == 3


def test_generation_changes_when_the_loaded_model_is_dropped():
    engine = make_engine()
    before = engine.generation
    asyncio.run(engine.unload())
    assert engine.generation == before + 1
