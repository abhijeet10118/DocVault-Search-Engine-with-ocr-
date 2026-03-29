import json

INDEX_FILE = "index.json"

def load_index():
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def search_word(word, index):
    word = word.lower()
    return index.get(word, [])

if __name__ == "__main__":
    index = load_index()

    while True:
        query = input("\n🔍 Enter word to search (or 'exit'): ")

        if query.lower() == "exit":
            break

        results = search_word(query, index)

        if results:
            print(f"📄 Found in documents: {results}")
        else:
            print("❌ No documents found")