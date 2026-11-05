from value_scanner.analysis.docs import DOCS_DIR, GURUS, render_all


def test_generated_docs_match_the_code():
    for name, text in render_all().items():
        path = DOCS_DIR / name
        assert path.exists(), f"{path} missing: run python -m value_scanner docs"
        assert path.read_text(encoding="utf-8") == text, (
            f"{name} is out of date: run python -m value_scanner docs"
        )


def test_every_criterion_is_documented():
    texts = render_all()
    for guru, (_, criteria) in GURUS.items():
        for cid in criteria:
            assert f"`{cid}`" in texts[f"{guru}.md"]
