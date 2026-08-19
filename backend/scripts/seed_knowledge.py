import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.database import engine
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.knowledge_ingestion import KnowledgeIngestionService
from app.services.knowledge_loader import KnowledgeLoader


DEFAULT_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base"


def seed(
    embedding_service: EmbeddingService | None = None,
    knowledge_dir: str | Path = DEFAULT_KNOWLEDGE_DIR,
    skip_existing: bool = True,
) -> None:
    if embedding_service is None:
        embedding_service = get_embedding_service()

    loader = KnowledgeLoader(knowledge_dir)

    with Session(engine) as session:
        service = KnowledgeIngestionService(session, embedding_service, loader)
        result = service.ingest_from_loader(skip_existing=skip_existing)

    print(
        f"Seeded knowledge base: {result.created} created, {result.skipped} skipped, "
        f"{len(result.errors)} errors"
    )
    if result.errors:
        for error in result.errors:
            print(f"  error: {error}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the knowledge base from JSON files.")
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_KNOWLEDGE_DIR,
        help="Directory containing knowledge JSON/JSONL files",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing knowledge entries before seeding",
    )
    args = parser.parse_args()

    if args.reset:
        print("Truncating knowledge_entries table...")
        with engine.connect() as conn:
            conn.exec_driver_sql("TRUNCATE TABLE knowledge_entries RESTART IDENTITY CASCADE")
            conn.commit()

    seed(knowledge_dir=args.path, skip_existing=not args.reset)


if __name__ == "__main__":
    main()
