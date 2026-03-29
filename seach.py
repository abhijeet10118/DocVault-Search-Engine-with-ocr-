from elasticsearch import Elasticsearch



from elasticsearch import Elasticsearch

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", "eoTny-muxm_VZR1BCOO*"),
    verify_certs=False
)

INDEX_NAME = "documents"

def search(query):
    body = {
        "query": {
            "match": {
                "content": query
            }
        }
    }

    res = es.search(index="documents", body=body)

    for hit in res["hits"]["hits"]:
        print(hit["_source"]["filename"], hit["_score"])

if __name__ == "__main__":
    while True:
        q = input("\n🔍 Search (or 'exit'): ")

        if q == "exit":
            break

        search(q)