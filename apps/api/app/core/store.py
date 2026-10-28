import copy
import threading
from pathlib import Path

from sqlalchemy import JSON, String, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document: Mapped[dict] = mapped_column(JSON)


class AttemptRecord(Base):
    __tablename__ = "attempts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, index=True)
    document: Mapped[dict] = mapped_column(JSON)


class VerificationRecord(Base):
    __tablename__ = "verifications"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, index=True)
    document: Mapped[dict] = mapped_column(JSON)


class FeedbackRecord(Base):
    __tablename__ = "verification_feedback"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, index=True)
    document: Mapped[dict] = mapped_column(JSON)


class Store:
    """Small transactional document store with schema-validated domain payloads.

    A single-process lock prevents lost JSON updates in the development job runner.
    Use one API worker; production needs a durable queue and row-level concurrency.
    """

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.lock = threading.RLock()

    def projects(self) -> list[dict]:
        with self.lock, Session(self.engine) as session:
            rows = session.scalars(select(ProjectRecord)).all()
            return sorted(
                [copy.deepcopy(row.document) for row in rows], key=lambda row: row["created_at"], reverse=True
            )

    def project(self, project_id: str) -> dict | None:
        with self.lock, Session(self.engine) as session:
            row = session.get(ProjectRecord, project_id)
            return copy.deepcopy(row.document) if row else None

    def save_project(self, document: dict) -> dict:
        with self.lock, Session(self.engine) as session:
            session.merge(ProjectRecord(id=document["id"], document=copy.deepcopy(document)))
            session.commit()
        return document

    def mutate_project(self, project_id: str, update) -> dict | None:
        with self.lock:
            document = self.project(project_id)
            if document is None:
                return None
            update(document)
            return self.save_project(document)

    def attempts(self, project_id: str) -> list[dict]:
        with self.lock, Session(self.engine) as session:
            rows = session.scalars(select(AttemptRecord).where(AttemptRecord.project_id == project_id)).all()
            return sorted(
                [copy.deepcopy(row.document) for row in rows], key=lambda row: row["created_at"], reverse=True
            )

    def attempt(self, attempt_id: str) -> dict | None:
        with self.lock, Session(self.engine) as session:
            row = session.get(AttemptRecord, attempt_id)
            return copy.deepcopy(row.document) if row else None

    def save_attempt(self, document: dict) -> dict:
        with self.lock, Session(self.engine) as session:
            session.merge(
                AttemptRecord(
                    id=document["id"], project_id=document["project_id"], document=copy.deepcopy(document)
                )
            )
            session.commit()
        return document

    def delete_project(self, project_id: str):
        with self.lock, Session(self.engine) as session:
            row = session.get(ProjectRecord, project_id)
            if row:
                session.delete(row)
            for attempt in session.scalars(
                select(AttemptRecord).where(AttemptRecord.project_id == project_id)
            ):
                session.delete(attempt)
            session.execute(delete(VerificationRecord).where(VerificationRecord.project_id == project_id))
            session.execute(delete(FeedbackRecord).where(FeedbackRecord.project_id == project_id))
            session.commit()

    def verifications(self, project_id: str) -> list[dict]:
        with self.lock, Session(self.engine) as session:
            rows = session.scalars(select(VerificationRecord).where(
                VerificationRecord.project_id == project_id
            )).all()
            return sorted([copy.deepcopy(row.document) for row in rows],
                          key=lambda item: item["created_at"], reverse=True)

    def save_verification(self, document: dict):
        with self.lock, Session(self.engine) as session:
            session.merge(VerificationRecord(id=document["id"], project_id=document["workflow_id"],
                                             document=copy.deepcopy(document)))
            session.commit()
            rows = session.scalars(select(VerificationRecord).where(
                VerificationRecord.project_id == document["workflow_id"]
            )).all()
            for row in sorted(rows, key=lambda item: item.document["created_at"], reverse=True)[100:]:
                session.delete(row)
            session.commit()
        return document

    def save_feedback(self, project_id: str, document: dict):
        with self.lock, Session(self.engine) as session:
            session.merge(FeedbackRecord(id=document["id"], project_id=project_id,
                                        document=copy.deepcopy(document)))
            session.commit()
            rows = session.scalars(select(FeedbackRecord).where(
                FeedbackRecord.project_id == project_id
            )).all()
            for row in sorted(rows, key=lambda item: item.document["created_at"], reverse=True)[100:]:
                session.delete(row)
            session.commit()
        return document

    def feedback(self, project_id: str):
        with self.lock, Session(self.engine) as session:
            rows = session.scalars(select(FeedbackRecord).where(
                FeedbackRecord.project_id == project_id
            )).all()
            return [copy.deepcopy(row.document) for row in rows]
