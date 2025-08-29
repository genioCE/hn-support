import os, argparse, pathlib, uuid
from typing import List, Tuple
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from tqdm import tqdm

def read_text_from_path(p: pathlib.Path) -> str:
    if p.suffix.lower() in {".md", ".txt"}:
        return p.read_text(errors="ignore")
    if p.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(str(p))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception as e:
            print(f"[WARN] Failed to parse PDF {p}: {e}")
            return ""
    return ""

def chunk_text(text: str, words_per_chunk: int = 300, overlap: int = 60) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i+words_per_chunk]
        chunks.append(" ".join(chunk))
        i += words_per_chunk - overlap
    return chunks

def ensure_collection(client: QdrantClient, name: str, dim: int, recreate: bool=False):
    exists = False
    try:
        info = client.get_collection(name)
        exists = True
    except Exception:
        exists = False
    if exists and recreate:
        client.delete_collection(name)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE)
        )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-dir", default="/kb")
    ap.add_argument("--collection", default="kb")
    ap.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://localhost:6333"))
    ap.add_argument("--model", default=os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    ap.add_argument("--recreate", action="store_true", help="Drop & recreate collection")
    args = ap.parse_args()

    kb_dir = pathlib.Path(args.kb_dir)
    assert kb_dir.is_dir(), f"{kb_dir} does not exist"

    model = SentenceTransformer(args.model)
    # Derive vector dim from model
    dim = model.get_sentence_embedding_dimension()

    client = QdrantClient(url=args.qdrant_url)
    ensure_collection(client, args.collection, dim, recreate=args.recreate)

    files = [p for p in kb_dir.rglob("*") if p.suffix.lower() in {".md", ".txt", ".pdf"}]
    points = []
    for p in tqdm(files, desc="Embedding"):
        text = read_text_from_path(p)
        for i, chunk in enumerate(chunk_text(text)):
            vec = model.encode(chunk, normalize_embeddings=True)
            pid = str(uuid.uuid4())
            payload = {
                "path": str(p),
                "chunk_id": i,
                "source": p.name,
                "text": chunk,
            }
            points.append(qm.PointStruct(id=pid, vector=vec.tolist(), payload=payload))
            # Batch insert every 256 points
            if len(points) >= 256:
                client.upsert(collection_name=args.collection, points=points)
                points.clear()

    if points:
        client.upsert(collection_name=args.collection, points=points)

    print("Done.")

if __name__ == "__main__":
    main()
