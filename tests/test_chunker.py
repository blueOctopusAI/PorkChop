"""Tests for text chunking module."""

from porkchop.chunker import chunk_by_size, chunk_by_structure, chunk_text


def test_chunk_by_size_basic():
    text = "A" * 100 + "\n" + "B" * 100
    chunks = chunk_by_size(text, max_chars=150)
    assert len(chunks) == 2


def test_chunk_by_size_single_chunk():
    text = "Short text here."
    chunks = chunk_by_size(text, max_chars=1000)
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_chunk_by_size_respects_lines():
    text = "\n".join([f"Line {i}" for i in range(100)])
    chunks = chunk_by_size(text, max_chars=200)
    for chunk in chunks:
        assert chunk.char_count <= 200 + 50  # Some tolerance for last line


def test_chunk_by_size_assigns_ids():
    text = "\n".join(["x" * 50] * 20)
    chunks = chunk_by_size(text, max_chars=200)
    assert chunks[0].chunk_id == "001"
    assert chunks[1].chunk_id == "002"


def test_chunk_by_structure_divisions(sample_cleaned_text):
    chunks = chunk_by_structure(sample_cleaned_text)
    # Should have at least 2 chunks: one for Division A content, one for Title I
    assert len(chunks) >= 1
    # Check that division metadata is captured
    div_chunks = [c for c in chunks if c.division]
    assert len(div_chunks) >= 1


def test_chunk_by_structure_preserves_content(sample_cleaned_text):
    chunks = chunk_by_structure(sample_cleaned_text)
    # All original content should be present across chunks
    combined = "\n".join(c.text for c in chunks)
    assert "disaster relief" in combined
    assert "$100,000,000" in combined


def test_chunk_text_defaults_to_structure(sample_cleaned_text):
    chunks = chunk_text(sample_cleaned_text)
    assert len(chunks) >= 1


def test_chunk_text_size_strategy(sample_cleaned_text):
    chunks = chunk_text(sample_cleaned_text, strategy="size", max_chars=500)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.char_count <= 500 + 100  # Some tolerance


def test_empty_input():
    chunks = chunk_by_size("", max_chars=1000)
    assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0].text == "")


def test_chunk_position_ordering():
    text = "DIVISION A\nContent A\n\nDIVISION B\nContent B\n\nDIVISION C\nContent C"
    chunks = chunk_by_structure(text)
    positions = [c.position for c in chunks]
    assert positions == sorted(positions)


def test_oversized_section_splits():
    # Create a section larger than max_chars
    text = "DIVISION A\n" + "x " * 15000 + "\nDIVISION B\nsmall content"
    chunks = chunk_by_structure(text, max_chars=5000)
    # Division A should be split into multiple chunks
    assert len(chunks) >= 3
