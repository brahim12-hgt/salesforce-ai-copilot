"""RAG léger: index TF-IDF des interactions + passages cités comme références."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from . import data_source


class RagIndex:
    def __init__(self):
        self.docs: list[dict] = []
        self.vec = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode")
        self.matrix = None

    def build(self, opp_ids: list[str]):
        self.docs = []
        for oid in opp_ids:
            for it in data_source.get_interactions(oid):
                self.docs.append({"opportunity_id": oid, **it})
        if self.docs:
            self.matrix = self.vec.fit_transform([d["text"] for d in self.docs])

    def search(self, query: str, k: int = 3, opp_id: str | None = None) -> list[dict]:
        if not self.docs:
            return []
        sims = cosine_similarity(self.vec.transform([query]), self.matrix)[0]
        ranked = sorted(zip(sims, self.docs), key=lambda t: t[0], reverse=True)
        return [d | {"score": round(float(s), 3)} for s, d in ranked
                if s > 0 and (opp_id is None or d["opportunity_id"] == opp_id)][:k]


index = RagIndex()
