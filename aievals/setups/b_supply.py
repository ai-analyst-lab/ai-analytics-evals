"""B-supply Supply / retrieval (cross-cutting, no single layer): how context REACHES the model.

Every other Track B unit decides WHAT context exists. This one decides how a piece of context
actually gets into the window at query time. C-supply-retrieval.md section 0 frames it as one
choice made per piece of context: does it arrive pre-loaded (full-context injection) or fetched
mid-run (retrieval)? The chapter names four delivery mechanisms ordered by how much the agent
decides for itself (full-context injection, lexical/keyword, vector RAG, agentic tool-call). The
load-bearing comparison for analytics is the first axis: inject the whole set versus retrieve only
the relevant top-k slice. Injecting everything is simple but rots past a point (single-fact
accuracy falls as the window fills with distractors); retrieving top-k keeps the window lean but
needs a way to find the relevant slice.

This module ships the part that is buildable now: the inject-versus-retrieve TOGGLE, as two
comparison arms over the same input set. The inject-all arm stages the full set; the retrieve-k
arm stages a top-k subset chosen by a simple, deterministic, provided scorer (lexical overlap,
the keyword/BM25-family mechanism of C-supply section 1.2, with no embedding dependency). The
scorer is swappable, so a richer mechanism can drop in later without touching the toggle.

The honest status is "partial". A real retrieval mechanism (vector RAG with contextual chunking
and rerank, the agentic retrieve->reason loop, the filter-first structured-store retrieval that
section 2 says the corrections log needs at scale) is more involved and is not built here. The
inject-versus-retrieve comparison the chapter recommends running on the corrections tail also
waits on B6 to supply a corrections-tail fixture; until then the toggle runs over whatever item
set the caller hands in (defaulting to our canonical meaning-only fixture).

There is no result number anywhere here. Which items get staged is computed from the input set and
the scorer at eval time; the count difference between the two arms is a property of the inputs and
k, never a literal baked into the module.
"""
import re
from pathlib import Path

from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text):
    """Lowercase word tokens of a string, as a set. The unit a lexical scorer compares over."""
    return set(_WORD.findall((text or "").lower()))


def lexical_overlap(query, text):
    """The default, deterministic scorer: how many query word-tokens appear in an item's text.

    This is the keyword/lexical mechanism of C-supply-retrieval.md section 1.2 (grep/BM25 family):
    zero build cost, never stale, no embedding dependency. It is intentionally simple and provided
    so the toggle has a working ranker; a caller can pass a richer scorer (or a real retriever)
    without changing the arms. Returns 0 for an empty query so an unspecified query is well-defined
    rather than an error."""
    q = _tokens(query)
    if not q:
        return 0
    return len(q & _tokens(text))


def _corpus_paths(items_dir=None):
    """The full input set: every *.yaml item in the directory, sorted for determinism. Defaults to
    our canonical fixture dir (no analyst path baked in); the caller supplies the corrections-tail
    or other item dir when running against a real store."""
    root = Path(items_dir) if items_dir is not None else FIXTURES
    return sorted(root.glob("*.yaml"))


def select_top_k(paths, query, k, scorer=None):
    """Rank the item paths by the scorer against the query and return the top-k. Deterministic:
    sort by score descending, breaking ties by path so the same inputs always yield the same slice.
    k is clamped to the available range, so retrieve-k never stages more than exists and never
    fewer than zero."""
    scorer = scorer or lexical_overlap
    scored = [(Path(p), scorer(query, Path(p).read_text())) for p in paths]
    ordered = sorted(scored, key=lambda ps: (-ps[1], str(ps[0])))
    k = max(0, min(k, len(ordered)))
    return [p for p, _ in ordered[:k]]


def inject_all(items_dir=None):
    """The inject-everything arm: stage the FULL item set in the window, no retrieval step. Simple
    and exact, but its footprint grows with the corpus and rots past a point (C-supply section
    1.1)."""
    paths = _corpus_paths(items_dir)
    return Setup(name="inject-all", layer=None, reader="file", spec=[str(p) for p in paths])


def retrieve_k(items_dir=None, query="", k=1, scorer=None):
    """The retrieve-top-k arm: stage only the k items the scorer ranks most relevant to the query.
    A lean window at the cost of a find step; the find step here is the lexical scorer (section
    1.2). The same input set as inject_all, narrowed to a subset."""
    top = select_top_k(_corpus_paths(items_dir), query, k, scorer)
    return Setup(name="retrieve-k", layer=None, reader="file", spec=[str(p) for p in top])


def staged_count(setup):
    """How many items a setup actually stages into the window. The footprint the comparison run
    reads off each arm; computed from the setup's overlays, not asserted."""
    return len(setup.read_overlays())


def build(items_dir=None, query="", k=1, scorer=None, **ctx):
    """Return the two comparison arms the supply run toggles over the SAME input set: inject-all
    (the whole set) versus retrieve-k (a top-k subset by the scorer). `items_dir` is the directory
    of item YAML (the corrections tail analyst-side, or any layer's item set); it defaults to our
    canonical fixture so the toggle is runnable hermetically with no analyst path baked in. For the
    same input set, inject-all stages at least as many items as retrieve-k, and strictly more
    whenever k is below the corpus size."""
    return [
        inject_all(items_dir),
        retrieve_k(items_dir, query=query, k=k, scorer=scorer),
    ]


register_setup(SetupSpec(
    key="B-supply",
    layer=None,                       # cross-cutting: the supply axis applies to any layer's items
    status="partial",
    summary=(
        "The inject-versus-retrieve toggle is buildable now: inject_all stages the full item set, "
        "retrieve_k stages a top-k subset by a simple deterministic lexical scorer (swappable). "
        "build() returns both arms over the same input set, so a comparison run can measure what "
        "retrieving instead of injecting does to footprint and reliability. A real retrieval "
        "mechanism (vector RAG, the agentic loop, filter-first structured-store retrieval) is "
        "more involved and is not built here."
    ),
    blocked_on=(
        "a real retrieval mechanism; the inject-vs-retrieve toggle is buildable, full retrieval "
        "(vector RAG with contextual chunking and rerank, the agentic retrieve->reason loop, the "
        "filter-first structured-store retrieval of C-supply-retrieval.md section 2) is later; the "
        "corrections-tail demo also waits on B6 to supply a corrections-tail fixture"
    ),
    source="C-supply-retrieval.md",
    build=build,
))
