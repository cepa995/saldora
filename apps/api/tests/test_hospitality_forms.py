"""Unit tests for the hospitality obligation matrix.

Pure-function tests — no DB or fixtures. The matrix is small enough
that we enumerate the cells explicitly rather than parameterising;
that way a regression in any one cell is a named test, not a single
failing parametrize id.
"""

from __future__ import annotations

from app.services.hospitality_forms import required_forms


def test_unclassified_client_marks_every_form_unclassified():
    """Both fields NULL → every form is "unclassified" (prompt to classify)."""
    result = required_forms(legal_form=None, bookkeeping_system=None)
    assert all(v == "unclassified" for v in result.values())


def test_pausalac_is_entirely_not_applicable():
    """Paušalci are out of scope (SRS Section 4.17) — no obligations."""
    result = required_forms(legal_form="paušalac", bookkeeping_system=None)
    assert all(v == "not_applicable" for v in result.values())

    # Even with a bookkeeping_system set, still all not_applicable.
    result = required_forms(legal_form="paušalac", bookkeeping_system="prosto")
    assert all(v == "not_applicable" for v in result.values())


def test_doo_dvojno_is_carved_out_of_dpu_and_pk1():
    """DOOs (dvojno-by-law) owe everything except DPU and PK-1.

    Mišljenje MF 011-00-761/2018-16 is the legal basis.
    """
    result = required_forms(legal_form="DOO", bookkeeping_system="dvojno")
    # Base hospitality forms are owed and have their real build status.
    assert result["kalkulacija"] == "pre_meeting"
    assert result["kep"] == "post_meeting"
    assert result["cenovnik"] == "post_meeting"
    assert result["popis"] == "post_meeting"
    # Prosto-only carve-outs.
    assert result["dpu"] == "not_applicable"
    assert result["pk1"] == "not_applicable"


def test_doo_without_explicit_bookkeeping_assumes_dvojno():
    """We don't make the agency double-check DOO → dvojno.

    Zakon o računovodstvu mandates double-entry for privredna društva,
    so the matrix treats DOO + NULL bookkeeping identically to DOO +
    dvojno.
    """
    explicit = required_forms(legal_form="DOO", bookkeeping_system="dvojno")
    implicit = required_forms(legal_form="DOO", bookkeeping_system=None)
    assert explicit == implicit


def test_preduzetnik_prosto_owes_everything():
    """Preduzetnik on prosto knjigovodstvo owes the full hospitality set."""
    result = required_forms(legal_form="preduzetnik", bookkeeping_system="prosto")
    assert result["kalkulacija"] == "pre_meeting"
    assert result["kep"] == "post_meeting"
    assert result["cenovnik"] == "post_meeting"
    assert result["popis"] == "post_meeting"
    assert result["dpu"] == "pre_meeting"
    assert result["pk1"] == "post_meeting"


def test_preduzetnik_dvojno_is_carved_out_of_dpu_and_pk1():
    """A preduzetnik can opt into dvojno; same carve-out as DOO."""
    result = required_forms(legal_form="preduzetnik", bookkeeping_system="dvojno")
    assert result["kalkulacija"] == "pre_meeting"
    assert result["kep"] == "post_meeting"
    assert result["cenovnik"] == "post_meeting"
    assert result["popis"] == "post_meeting"
    assert result["dpu"] == "not_applicable"
    assert result["pk1"] == "not_applicable"


def test_preduzetnik_without_bookkeeping_leaves_dpu_and_pk1_unclassified():
    """Preduzetnik + NULL bookkeeping is genuinely ambiguous on DPU/PK-1.

    The agency hasn't told us which system; surface the base obligations
    and flag DPU + PK-1 as unclassified so the obligation card prompts
    for the second field.
    """
    result = required_forms(legal_form="preduzetnik", bookkeeping_system=None)
    # Base forms come through with their build status.
    assert result["kalkulacija"] == "pre_meeting"
    assert result["kep"] == "post_meeting"
    assert result["cenovnik"] == "post_meeting"
    assert result["popis"] == "post_meeting"
    # The matrix can't decide without bookkeeping_system.
    assert result["dpu"] == "unclassified"
    assert result["pk1"] == "unclassified"


def test_drugo_falls_through_to_the_same_matrix_as_preduzetnik():
    """`drugo` (other) is treated as a generic legal form — still hospitality,
    still needs explicit bookkeeping to resolve DPU/PK-1."""
    result = required_forms(legal_form="drugo", bookkeeping_system="prosto")
    assert result["dpu"] == "pre_meeting"
    assert result["pk1"] == "post_meeting"

    result = required_forms(legal_form="drugo", bookkeeping_system="dvojno")
    assert result["dpu"] == "not_applicable"
    assert result["pk1"] == "not_applicable"


def test_every_call_returns_the_complete_form_set():
    """The matrix never omits a key — the frontend can render a full table
    without further enumeration."""
    expected_keys = {"kalkulacija", "kep", "cenovnik", "popis", "dpu", "pk1"}
    for legal, book in [
        (None, None),
        ("paušalac", None),
        ("DOO", None),
        ("DOO", "dvojno"),
        ("preduzetnik", None),
        ("preduzetnik", "prosto"),
        ("preduzetnik", "dvojno"),
        ("drugo", "prosto"),
    ]:
        result = required_forms(legal_form=legal, bookkeeping_system=book)
        assert set(result.keys()) == expected_keys, f"{legal=} {book=}"
