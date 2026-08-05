"""Unit tests for RAG pipeline components."""
import pytest
from app.rag.chunker import chunk_text
from app.agents.base_agent import extract_json


def test_chunk_text_basic():
    text = " ".join(["word"] * 1000)
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10, source_id="test")
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk.text.split()) <= 100 + 10  # allow slight overflow


def test_chunk_text_short_document():
    text = "This is a short document with only a few words."
    chunks = chunk_text(text, chunk_size=512, chunk_overlap=64, source_id="test")
    assert len(chunks) == 1
    assert "short document" in chunks[0].text


def test_chunk_text_empty():
    chunks = chunk_text("", chunk_size=100, chunk_overlap=10, source_id="test")
    assert chunks == []


def test_chunk_ids_are_unique():
    text = " ".join([f"sentence {i}. " for i in range(200)])
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=5, source_id="test")
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_extract_json_plain():
    result = extract_json('{"key": "value", "num": 42}')
    assert result == {"key": "value", "num": 42}


def test_extract_json_from_markdown():
    text = 'Here is the result:\n```json\n{"status": "ok"}\n```\nDone.'
    result = extract_json(text)
    assert result == {"status": "ok"}


def test_extract_json_array():
    text = '[{"name": "Alice"}, {"name": "Bob"}]'
    result = extract_json(text)
    assert isinstance(result, list)
    assert len(result) == 2


def test_extract_json_from_text_with_json():
    text = 'The answer is: {"concept": "Newton\'s law", "value": 3.14}'
    result = extract_json(text)
    assert result["concept"] == "Newton's law"


def test_extract_json_from_fenced_text_with_extra_content():
    text = 'Here is the answer:\n```json\n{\n  "learning_objectives": [\n    "Describe the preparation of alcohols."\n  ],\n  "prerequisites": []\n}\n```\nThank you.'
    result = extract_json(text)
    assert result["learning_objectives"] == ["Describe the preparation of alcohols."]


def test_extract_json_from_truncated_fenced_output():
    text = '''```json
{
  "learning_objectives": [
    "Name alcohols, phenols, and ethers according to the IUPAC nomenclature system",
    "Describe the methods of preparation of alcohols from alkenes, aldehydes, '
'''
    result = extract_json(text)
    assert result["learning_objectives"][0].startswith("Name alcohols")


def test_extract_json_with_trailing_commas():
    text = '{"learning_objectives": ["A"], "prerequisites": ["B",],}'
    result = extract_json(text)
    assert result["prerequisites"] == ["B"]


def test_extract_json_raises_on_invalid():
    with pytest.raises(ValueError):
        extract_json("This has no JSON in it at all.")
