"""Dados iniciais idempotentes: usuário demo, admin opcional e base de conhecimento de doenças (MySQL + Qdrant).

Unidades de saúde são criadas pela migration inicial. Execução: `python -m app.seed`.
"""

import asyncio

from app.core.config import Settings, get_settings
from app.core.constants import Severity, VectorCollection
from app.core.logging import get_logger, setup_logging
from app.core.security import hash_password
from app.db.models.user import User
from app.db.repositories.disease_repository import DiseaseRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.vector_repository import VectorRepository
from app.db.session import create_engine, create_session_factory
from app.integrations.qdrant_client import create_qdrant_client
from app.schemas.vector import DiseaseIndexRequest
from app.services.vector_service import VectorService

logger = get_logger("app.seed")

DEMO_USER = {"name": "Marina Santos", "email": "marina.santos@medflux.com", "password": "123456", "city": "Marília, SP"}

# Conteúdo educativo e genérico para dar contexto ao LLM; não substitui protocolo clínico.
DISEASES: list[DiseaseIndexRequest] = [
    DiseaseIndexRequest(
        name="Gripe (Influenza)",
        description="Infecção viral respiratória aguda, comum em épocas frias, geralmente autolimitada.",
        symptoms=["febre", "tosse", "dor no corpo", "dor de cabeça", "dor de garganta", "cansaço"],
        recommended_unit="UBS",
        severity=Severity.MILD,
    ),
    DiseaseIndexRequest(
        name="Resfriado comum",
        description="Infecção viral leve das vias aéreas superiores.",
        symptoms=["coriza", "espirros", "dor de garganta", "tosse leve", "nariz entupido"],
        recommended_unit="UBS",
        severity=Severity.MILD,
    ),
    DiseaseIndexRequest(
        name="COVID-19",
        description="Infecção pelo SARS-CoV-2; casos com falta de ar exigem avaliação urgente.",
        symptoms=["febre", "tosse", "perda de olfato", "perda de paladar", "cansaço", "falta de ar"],
        recommended_unit="UBS",
        severity=Severity.MODERATE,
    ),
    DiseaseIndexRequest(
        name="Dengue",
        description="Arbovirose transmitida pelo Aedes aegypti; sangramentos e dor abdominal intensa são sinais de alarme.",
        symptoms=["febre alta", "dor atrás dos olhos", "dor no corpo", "manchas vermelhas", "dor nas articulações"],
        recommended_unit="UPA",
        severity=Severity.URGENT,
    ),
    DiseaseIndexRequest(
        name="Gastroenterite aguda",
        description="Inflamação do trato gastrointestinal; risco principal é a desidratação.",
        symptoms=["diarreia", "vômito", "náusea", "dor abdominal", "febre baixa"],
        recommended_unit="UBS",
        severity=Severity.MODERATE,
    ),
    DiseaseIndexRequest(
        name="Infecção urinária",
        description="Infecção bacteriana do trato urinário; febre e dor lombar sugerem acometimento renal.",
        symptoms=["dor ao urinar", "ardência ao urinar", "vontade frequente de urinar", "urina turva"],
        recommended_unit="UBS",
        severity=Severity.MODERATE,
    ),
    DiseaseIndexRequest(
        name="Enxaqueca",
        description="Cefaleia primária recorrente; dor súbita e muito intensa ('a pior da vida') exige emergência.",
        symptoms=["dor de cabeça latejante", "sensibilidade à luz", "náusea", "visão alterada"],
        recommended_unit="UBS",
        severity=Severity.MILD,
    ),
    DiseaseIndexRequest(
        name="Crise asmática",
        description="Estreitamento das vias aéreas com dificuldade respiratória; crises intensas são emergência.",
        symptoms=["falta de ar", "chiado no peito", "tosse", "aperto no peito"],
        recommended_unit="UPA",
        severity=Severity.URGENT,
    ),
    DiseaseIndexRequest(
        name="Pneumonia",
        description="Infecção pulmonar que pode evoluir com gravidade em idosos e crianças.",
        symptoms=["febre alta", "tosse com catarro", "falta de ar", "dor no peito ao respirar", "cansaço"],
        recommended_unit="UPA",
        severity=Severity.URGENT,
    ),
    DiseaseIndexRequest(
        name="Infarto agudo do miocárdio",
        description="Emergência cardiovascular: ligar 192 imediatamente.",
        symptoms=["dor no peito", "dor irradiando para o braço", "suor frio", "falta de ar", "náusea"],
        recommended_unit="UPA",
        severity=Severity.EMERGENCY,
    ),
    DiseaseIndexRequest(
        name="Acidente vascular cerebral (AVC)",
        description="Emergência neurológica: ligar 192 imediatamente; tempo é decisivo.",
        symptoms=["boca torta", "fraqueza de um lado do corpo", "fala enrolada", "perda de visão", "tontura súbita"],
        recommended_unit="UPA",
        severity=Severity.EMERGENCY,
    ),
    DiseaseIndexRequest(
        name="Apendicite",
        description="Inflamação do apêndice que pode exigir cirurgia de urgência.",
        symptoms=["dor abdominal no lado direito", "febre", "náusea", "vômito", "perda de apetite"],
        recommended_unit="UPA",
        severity=Severity.URGENT,
    ),
    DiseaseIndexRequest(
        name="Hipertensão arterial",
        description="Pressão alta crônica; dor de cabeça forte com alteração visual pode indicar crise hipertensiva.",
        symptoms=["pressão alta", "dor de cabeça", "tontura", "visão embaçada"],
        recommended_unit="UBS",
        severity=Severity.MODERATE,
    ),
]


async def _ensure_user(
    users: UserRepository, settings: Settings, *, name: str, email: str, password: str, city: str, is_admin: bool
) -> None:
    if await users.get_by_email(email):
        logger.info("seed_user_exists", extra={"email": email})
        return
    await users.add(
        User(
            name=name,
            email=email,
            city=city,
            is_admin=is_admin,
            password_hash=hash_password(password, settings.BCRYPT_ROUNDS),
        )
    )
    logger.info("seed_user_created", extra={"email": email, "is_admin": is_admin})


async def seed(settings: Settings) -> None:
    engine = create_engine(settings)
    qdrant = create_qdrant_client(settings)
    try:
        async with create_session_factory(engine)() as session:
            users = UserRepository(session)
            if settings.SEED_DEMO_USER and settings.APP_ENV != "production":
                await _ensure_user(users, settings, **DEMO_USER, is_admin=False)
            if settings.SEED_ADMIN_EMAIL and settings.SEED_ADMIN_PASSWORD:
                await _ensure_user(
                    users,
                    settings,
                    name="Administrador MedFlux",
                    email=settings.SEED_ADMIN_EMAIL.strip().lower(),
                    password=settings.SEED_ADMIN_PASSWORD,
                    city="",
                    is_admin=True,
                )
            await session.commit()

            vectors = VectorRepository(qdrant, settings.EMBEDDING_DIM)
            try:
                await vectors.ensure_collections(VectorCollection)
                service = VectorService(vectors, settings.EMBEDDING_DIM, DiseaseRepository(session))
                for disease in DISEASES:
                    await service.index_disease(disease)
                await session.commit()
                logger.info("seed_diseases_indexed", extra={"count": len(DISEASES)})
            except Exception as exc:  # noqa: BLE001 - sem Qdrant o seed do MySQL continua válido
                await session.rollback()
                logger.warning("seed_diseases_skipped_qdrant_unavailable", extra={"error": type(exc).__name__})
    finally:
        await qdrant.close()
        await engine.dispose()


if __name__ == "__main__":
    current = get_settings()
    setup_logging(current.LOG_LEVEL)
    asyncio.run(seed(current))
