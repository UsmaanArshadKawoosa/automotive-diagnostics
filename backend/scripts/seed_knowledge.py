from sqlalchemy.orm import Session

from app.db.database import engine
from app.db.models import KnowledgeEntry
from app.services.embeddings import EmbeddingService, get_embedding_service


SAMPLE_ENTRIES: list[dict[str, str | None]] = [
    {
        "category": "symptom",
        "entry_key": "engine_misfire",
        "content": "Engine misfire is often caused by faulty spark plugs, ignition coils, or fuel injectors. Common accompanying signs include rough idle and loss of power.",
        "source": "automotive-diagnostics-v1",
    },
    {
        "category": "symptom",
        "entry_key": "rough_idle",
        "content": "Rough idle can be caused by vacuum leaks, dirty throttle body, faulty ignition coils, or worn spark plugs.",
        "source": "automotive-diagnostics-v1",
    },
    {
        "category": "dtc",
        "entry_key": "P0300",
        "content": "P0300 indicates random or multiple cylinder misfires. Inspect spark plugs, ignition coils, fuel injectors, and compression.",
        "source": "OBD-II reference",
    },
    {
        "category": "dtc",
        "entry_key": "P0301",
        "content": "P0301 indicates a misfire detected in cylinder 1. Check spark plug, ignition coil, and injector for cylinder 1.",
        "source": "OBD-II reference",
    },
    {
        "category": "fault",
        "entry_key": "ignition_coil_failure",
        "content": "A failed ignition coil can cause misfires, rough running, and reduced fuel economy. Replacement is the typical repair.",
        "source": "automotive-diagnostics-v1",
    },
    {
        "category": "repair",
        "entry_key": "spark_plug_replacement",
        "content": "Replace spark plugs at the manufacturer-recommended interval or when misfires are present. Use the correct plug type and torque specification.",
        "source": "automotive-diagnostics-v1",
    },
    {
        "category": "component",
        "entry_key": "mass_air_flow_sensor",
        "content": "The mass air flow (MAF) sensor measures incoming air. A dirty or failing MAF sensor can cause rough idle, hesitation, and poor fuel economy.",
        "source": "automotive-diagnostics-v1",
    },
    {
        "category": "symptom",
        "entry_key": "poor_acceleration",
        "content": "Poor acceleration may be caused by clogged air filter, failing fuel pump, restricted catalytic converter, or faulty throttle position sensor.",
        "source": "automotive-diagnostics-v1",
    },
]


def seed(embedding_service: EmbeddingService | None = None) -> None:
    if embedding_service is None:
        embedding_service = get_embedding_service()

    texts = [
        f"{entry['category']} {entry['entry_key'] or ''} {entry['content']}".strip()
        for entry in SAMPLE_ENTRIES
    ]
    embeddings = embedding_service.embed(texts)

    with Session(engine) as session:
        for entry_data, embedding in zip(SAMPLE_ENTRIES, embeddings):
            session.add(KnowledgeEntry(**entry_data, embedding=embedding))
        session.commit()
        print(f"Seeded {len(SAMPLE_ENTRIES)} knowledge entries")


if __name__ == "__main__":
    seed()
