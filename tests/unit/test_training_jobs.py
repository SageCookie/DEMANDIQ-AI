from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.routes import _serialize_training_job
from src.database.models import Base, TrainingJob


def test_training_job_is_persisted_and_serialized():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    job = TrainingJob(id="job-1", status="QUEUED", progress=0, message="Queued for training", requested_by="scientist")
    session.add(job)
    session.commit()

    payload = _serialize_training_job(session.query(TrainingJob).one())
    assert payload["id"] == "job-1"
    assert payload["status"] == "QUEUED"
    assert payload["progress"] == 0
    assert payload["requested_by"] == "scientist"
