
from elasticsearch import Elasticsearch
import os
from extract_text import extract_text

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", "eoTny-muxm_VZR1BCOO*"),
    verify_certs=False,
    ssl_show_warn=False
)
es.indices.delete(index="documents", ignore=[400, 404])
print("✅ Index deleted")

print(es.info())


INDEX_NAME = "documents"
DOC_PATH = "documents"

def create_index():
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME)

def index_documents():
    for filename in os.listdir(DOC_PATH):
        filepath = os.path.join(DOC_PATH, filename)

        if os.path.isfile(filepath):
            content = extract_text(filepath)

            if content.strip() == "":
                continue

            doc = {
                "filename": filename,
                "content": content
            }

            es.index(
                index=INDEX_NAME,
                id=filename,
                document=doc
            )

            print(f"✅ Indexed: {filename}")

if __name__ == "__main__":
    create_index()
    index_documents()