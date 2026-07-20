from talent_radar.services.query_pack import QueryPack, QueryPackMatcher


def matcher() -> QueryPackMatcher:
    pack = QueryPack(
        entity="VSF",
        version="test",
        exact=["VSF", "VinSmart Future"],
        aliases=["VFS"],
        ecosystem_slang=["Vin do", "cong ty cong nghe Vin"],
        location_indirect=["Technopark"],
        context_anchors=["chuong trinh", "dang ky", "mentor"],
        exclusions=["VinFast", "VinFuture Prize"],
    )
    return QueryPackMatcher(pack)


def test_exact_match_is_relevant() -> None:
    result = matcher().match("VSF co deadline dang ky chua?")
    assert result["label"] == "relevant"
    assert "VSF" in result["matched_terms"]


def test_slang_without_context_needs_review() -> None:
    result = matcher().match("cong ty cong nghe Vin o Technopark nghe noi moi lam gi do")
    assert result["label"] == "possibly_relevant"
    assert result["needs_review"] is True


def test_exclusion_blocks_without_anchor() -> None:
    result = matcher().match("VinFast ra xe moi")
    assert result["label"] == "irrelevant"
