from navigator.embed import CHUNK_MAX, chunk


def test_chunk_limits_and_title():
    para = " ".join(["word"] * 120) + "."
    text = "\n".join([para] * 7)                      # 840 words in 7 paragraphs
    chunks = chunk("Title", text)
    assert all(c.startswith("Title\n") for c in chunks)
    assert all(len(c.split()) - 1 <= CHUNK_MAX for c in chunks)
    assert sum(len(c.split()) - 1 for c in chunks) == 840


def test_long_paragraph_split_at_sentences():
    para = " ".join(f"Sentence number {i} has some words." for i in range(100))   # 600 words, one paragraph
    assert len(chunk("T", para)) == 2


def test_short_tail_joins_previous():
    text = " ".join(["a"] * 300) + "\n" + " ".join(["b"] * 40)
    assert len(chunk("T", text)) == 1
