import hashlib
import re
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from src.debug import log


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CHROMA_PATH = _PROJECT_ROOT / ".chroma"
_COLLECTION_NAME = "college_records"


class ChromaIndex:
 
    _embedding_function = None

    @classmethod
    def _get_embedding_function(cls):
        if cls._embedding_function is None:
            cls._embedding_function = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2",
                local_files_only=True,
            )
        return cls._embedding_function

    def __init__(self, records, text_fn):
        self.records_by_id = {r["college_id"]: r for r in records}
        self.client = chromadb.PersistentClient(path=str(_CHROMA_PATH))
        self.collection = self.client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self._get_embedding_function(),
        )
        self._upsert_changed_records(records, text_fn)

    def _upsert_changed_records(self, records, text_fn):
        """Store new or changed records; leave unchanged vectors in Chroma."""
        ids = [r["college_id"] for r in records]
        documents = [text_fn(r) for r in records]
        hashes = [hashlib.sha256(doc.encode()).hexdigest() for doc in documents]
        existing = self.collection.get(ids=ids, include=["metadatas"])
        existing_hashes = {
            college_id: metadata.get("record_hash")
            for college_id, metadata in zip(existing["ids"], existing["metadatas"])
        }

        changed = [
            (college_id, document, record_hash)
            for college_id, document, record_hash in zip(ids, documents, hashes)
            if existing_hashes.get(college_id) != record_hash
        ]
        if changed:
            self.collection.upsert(
                ids=[college_id for college_id, _, _ in changed],
                documents=[document for _, document, _ in changed],
                metadatas=[{"record_hash": record_hash} for _, _, record_hash in changed],
            )
        log("5. vector-index synchronization", {"records": len(records), "upserted": [college_id for college_id, _, _ in changed]})

    def search(self, query, top_k=5, min_score=0.25):
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, len(self.records_by_id)),
            include=["distances"],
        )
        hits = []
        for college_id, distance in zip(results["ids"][0], results["distances"][0]):
            score = 1 - distance  # Chroma cosine distance -> similarity score
            if score >= min_score:
                hits.append((self.records_by_id[college_id], score))
        return hits

def _course_matches(record, keyword):
    keyword = keyword.lower()
    # NOTE: a Diploma is explicitly NOT a degree per the data dictionary.
    return any(keyword in c.lower() for c in record["courses_offered"])


def structural_filter(records, course_kw=None, city=None, r_type=None,
                       hostel=None, min_cutoff_below=None, is_government=None):
    out = records
    if course_kw:
        out = [r for r in out if _course_matches(r, course_kw)]
    if city:
        out = [r for r in out if r["city"].lower() == city.lower()]
    if r_type:
        out = [r for r in out if r["type"].lower() == r_type.lower()]
    if is_government:
        out = [r for r in out if r["type"].lower() == "government"]
    if hostel is not None:
        out = [r for r in out if r["hostel_available"] == hostel]
    if min_cutoff_below is not None:
        # Cutoff is a HARD FLOOR: a student is eligible only if their
        # score is >= last_year_cutoff_pct. NOT a percentile/rank.
        out = [r for r in out if r["last_year_cutoff_pct"] <= min_cutoff_below]
    return out


LISTING_WORDS = {"list", "which", "all"}
COURSE_ALIASES = {
    "engineering": "B.Tech",
    "engg": "B.Tech",
    "mba": "MBA",
    "phd": "PhD",
    "diploma": "Diploma",
}


def _detect_course_keyword(q_lower):
    for alias, canonical in COURSE_ALIASES.items():
        if alias in q_lower:
            return canonical
    return None


def retrieve(records, query, top_k=6, parsed=None):
    
    idx = ChromaIndex(records, lambda r: f"{r['name']} {r['city']} {r['about']}")
    semantic_hits = idx.search(query, top_k=top_k)
    freetext_hits = [r for r, _ in semantic_hits]

    q_lower = query.lower()
    name_hits = [
        r for r in records
        if any(word in q_lower for word in r["name"].lower().split() if len(word) > 3)
    ]

    parsed = parsed or {}

    mentioned = parsed.get("mentioned_college_name")
    mentioned_hits = []
    if mentioned:
        m_lower = mentioned.lower()
        mentioned_hits = [
            r for r in records
            if m_lower in r["name"].lower() or r["name"].lower() in m_lower
        ]

    course_kw = parsed.get("course_keyword") or _detect_course_keyword(q_lower)
    is_gov = parsed.get("wants_government_only")
    if is_gov is None:
        is_gov = "government" in q_lower or None
    hostel = parsed.get("wants_hostel")
    if hostel is None:
        hostel = True if "hostel" in q_lower else None
    is_listing = parsed.get("is_listing_question") or any(w in q_lower for w in LISTING_WORDS)

    structural_hits = []
    if is_listing:
        structural_hits = structural_filter(
            records, course_kw=course_kw, is_government=is_gov, hostel=hostel,
        )

    log("5. retrieval signals", {
        "course_keyword": course_kw,
        "government_only": is_gov,
        "hostel": hostel,
        "listing_question": is_listing,
        "mentioned_college": mentioned,
    })
    log("5. retrieval candidates", {
        "semantic": [{"college_id": r["college_id"], "score": round(score, 3)} for r, score in semantic_hits],
        "mentioned": [r["college_id"] for r in mentioned_hits],
        "structural": [r["college_id"] for r in structural_hits],
        "name": [r["college_id"] for r in name_hits],
    })

    seen, merged = set(), []
    for r in mentioned_hits + structural_hits + name_hits + freetext_hits:
        if r["college_id"] not in seen:
            seen.add(r["college_id"])
            merged.append(r)
    cap = max(top_k, len(structural_hits))  
    selected = merged[:cap] if merged else records[:top_k]  
    log("5. retrieval selection", [r["college_id"] for r in selected])
    return selected
