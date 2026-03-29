"""
Management command: sync_es_index
----------------------------------
Removes any Elasticsearch entries that no longer have a matching
Document row in the database.

Usage:
    python manage.py sync_es_index          # dry run (shows what would be deleted)
    python manage.py sync_es_index --apply  # actually deletes stale entries
    python manage.py sync_es_index --wipe   # deletes the ENTIRE index (nuclear option)
"""

from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch
from core.models import Document          # adjust 'core' to your app name if different

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", "eoTny-muxm_VZR1BCOO*"),
    verify_certs=False
)

INDEX = "documents"


class Command(BaseCommand):
    help = "Sync the Elasticsearch index with the database"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Actually delete stale ES entries')
        parser.add_argument('--wipe',  action='store_true', help='Delete the entire ES index and rebuild from DB')

    def handle(self, *args, **options):
        if options['wipe']:
            self._wipe_and_rebuild()
            return

        self._remove_stale(apply=options['apply'])

    # ── wipe entire index and re-index everything in DB ──────────────────

    def _wipe_and_rebuild(self):
        self.stdout.write(self.style.WARNING("Deleting entire ES index…"))
        try:
            es.indices.delete(index=INDEX, ignore=[400, 404])
            self.stdout.write(self.style.SUCCESS("Index deleted."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Could not delete index: {e}"))
            return

        from core.extract_text import extract_text   # lazy import

        docs = Document.objects.all()
        ok = skipped = 0
        for doc in docs:
            try:
                import os
                if not os.path.isfile(doc.file.path):
                    self.stdout.write(f"  SKIP (no file on disk): {doc.title}")
                    skipped += 1
                    continue
                content = extract_text(doc.file.path)
                if not content.strip():
                    skipped += 1
                    continue
                es.index(index=INDEX, id=doc.id, document={
                    "filename": doc.title,
                    "content": content,
                    "branch": doc.branch,
                    "doc_id": doc.id,
                })
                ok += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ERROR indexing {doc.title}: {e}"))
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Re-indexed {ok} docs, skipped {skipped}."))

    # ── remove stale entries ──────────────────────────────────────────────

    def _remove_stale(self, apply: bool):
        # Fetch all doc IDs currently in ES
        try:
            res = es.search(index=INDEX, body={"query": {"match_all": {}}, "size": 10000, "_source": False})
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ES search failed: {e}"))
            return

        es_ids = {int(hit["_id"]) for hit in res["hits"]["hits"]}
        db_ids = set(Document.objects.values_list("id", flat=True))

        stale = es_ids - db_ids

        if not stale:
            self.stdout.write(self.style.SUCCESS("ES index is clean — no stale entries found."))
            return

        self.stdout.write(f"Found {len(stale)} stale ES entries: {sorted(stale)}")

        if not apply:
            self.stdout.write(self.style.WARNING("Dry run. Pass --apply to actually delete them."))
            return

        deleted = 0
        for es_id in stale:
            try:
                es.delete(index=INDEX, id=es_id)
                deleted += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Could not delete ES id={es_id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} stale entries from ES index."))