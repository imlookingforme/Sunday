import tempfile
import pytest
from pathlib import Path
from sunday.core.intelligence.biometric_verifier import BiometricVerifier
from sunday.core.intelligence.sentience_engine import SentienceEngine
from sunday.core.tutoring.socratic_tutor import SocraticTutor


@pytest.mark.asyncio
async def test_biometric_verifier(tmp_path: Path):
    db_path = tmp_path / "test_voice.db"
    verifier = BiometricVerifier(db_path=db_path)

    # Enroll speaker
    sample_file = tmp_path / "sample1.wav"
    sample_file.write_bytes(b"RIFFdummydataforvoiceanalysis12345")

    success = await verifier.enroll_speaker("raghuram", [sample_file])
    assert success is True

    # Identify speaker
    speaker, conf = await verifier.identify_speaker(sample_file)
    assert speaker == "raghuram"
    assert conf > 0.4

    # Greeting check
    greeting = verifier.get_greeting("raghuram")
    assert "Welcome back" in greeting


@pytest.mark.asyncio
async def test_sentience_engine_reflection(tmp_path: Path):
    db_path = tmp_path / "test_reflections.db"
    engine = SentienceEngine(db_path=db_path)

    res = await engine.force_reflection()
    assert "journal_entry" in res
    assert res["insights_count"] >= 1

    last = await engine.get_last_reflection()
    assert last is not None
    assert last["insights_count"] == res["insights_count"]


@pytest.mark.asyncio
async def test_socratic_tutor(tmp_path: Path):
    db_path = tmp_path / "test_study.db"
    tutor = SocraticTutor(db_path=db_path)

    prompt = tutor.generate_prompt("Quantum Mechanics", style="socratic")
    assert "guiding questions" in prompt

    plan = tutor.create_study_plan("Calculus III", duration_hours=1)
    assert plan["total_blocks"] == 2

    await tutor.track_progress("Calculus III", duration_minutes=50, score=0.9)
    report = await tutor.get_progress_report("Calculus III")
    assert report["total_sessions"] == 1
    assert report["average_mastery_score"] == 0.9
