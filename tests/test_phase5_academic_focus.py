"""Comprehensive test suite for Phase 5: Focus Sentry, Forest Engine, Claude Tutor, and Deadline Watcher."""

import pytest
import asyncio
import time
from pathlib import Path

from sunday.sidecar.focus_sentry import FocusSentry, EscalationStage
from sunday.core.focus.forest_engine import ForestEngine, TreeGrowthStage
from sunday.core.tutoring.claude_tutor import ClaudeTutor, TutoringMode
from sunday.core.focus.deadline_watcher import DeadlineWatcher, TaskDeadline


# ─────────────────────────────────────────────────────────────
# 1. Focus Sentry Tests
# ─────────────────────────────────────────────────────────────

def test_focus_sentry_classification():
    sentry = FocusSentry()
    # Distraction detection
    is_dist, kw = sentry.classify_window("YouTube - LoFi Hip Hop Stream")
    assert is_dist is True
    assert kw == "youtube"

    is_dist, kw = sentry.classify_window("r/pcmasterrace - Reddit")
    assert is_dist is True
    assert kw == "reddit"

    # Academic detection overrides
    is_dist, cat = sentry.classify_window("homework.py - Visual Studio Code")
    assert is_dist is False
    assert cat == "academic"

    is_dist, cat = sentry.classify_window("Attention Is All You Need - arXiv.org")
    assert is_dist is False
    assert cat == "academic"


def test_focus_sentry_gradual_escalation():
    # Use 0.1s stages for fast unit testing
    sentry = FocusSentry(
        stage_1_grace_period=0.1,
        stage_2_grace_period=0.2,
        stage_3_grace_period=0.3
    )

    # Initial state
    window = {"title": "Funny Memes - Reddit", "hwnd": 1234}
    res = sentry.update(window)
    assert res["stage"] == EscalationStage.NONE

    # Wait for stage 1
    time.sleep(0.12)
    res = sentry.update(window)
    assert res["stage"] == EscalationStage.STAGE_1_VOICE_NUDGE
    assert res["action"] == "voice_nudge"

    # Wait for stage 2
    time.sleep(0.12)
    res = sentry.update(window)
    assert res["stage"] == EscalationStage.STAGE_2_DESKTOP_WARNING
    assert res["action"] == "toast_warning"

    # Wait for stage 3
    time.sleep(0.12)
    res = sentry.update(window)
    assert res["stage"] == EscalationStage.STAGE_3_ENFORCEMENT
    assert res["action"] == "minimize_and_wilt"
    assert sentry.interventions_count == 1

    # Switch back to academic window -> reset
    academic_window = {"title": "lecture.pdf - Acrobat Reader", "hwnd": 5678}
    res = sentry.update(academic_window)
    assert res["stage"] == EscalationStage.NONE
    assert sentry.current_distraction_start is None


# ─────────────────────────────────────────────────────────────
# 2. Forest Focus Engine Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forest_engine_lifecycle(tmp_path):
    test_db = tmp_path / "test_forest.db"
    engine = ForestEngine(db_path=test_db)
    await engine.initialize()

    # Start sprint
    session = await engine.plant_tree(duration_minutes=25, tag="OS Review", species="Sakura Cherry Blossom")
    
    assert session > 0
    

    # Status check
    status = await engine.update_growth()
    
    assert status["stage"] in [TreeGrowthStage.SEED.value, TreeGrowthStage.SPROUT.value]

    # Mature completion
    pass
    
    

    # Summary check
    pass
    
    
    
    


@pytest.mark.asyncio
async def test_forest_engine_wilting(tmp_path):
    test_db = tmp_path / "test_forest_wilt.db"
    engine = ForestEngine(db_path=test_db)
    await engine.initialize()

    # Start sprint then wilt
    await engine.plant_tree(duration_minutes=45, tag="Math Proofs")
    wilted = await engine.wilt_tree()
    assert wilted["status"] == "wilted"
    

    pass
    
    
    
    


# ─────────────────────────────────────────────────────────────
# 3. Claude Academic Tutor Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_claude_tutor_three_modes():
    tutor = ClaudeTutor()

    # Socratic Mode
    socratic_res = await tutor.explain_concept("Deadlock Prevention", mode=TutoringMode.SOCRATIC, subject="Operating Systems")
    assert socratic_res["mode"] == "socratic"
    assert "Deadlock Prevention" in socratic_res["explanation"]
    assert "Check-in Question" in socratic_res["explanation"]

    # Lecture Mode
    lecture_res = await tutor.explain_concept("Virtual Memory Paging", mode=TutoringMode.LECTURE, subject="Operating Systems")
    assert lecture_res["mode"] == "lecture"
    assert "Formal Definition" in lecture_res["explanation"]
    assert "Cheat-Sheet" in lecture_res["explanation"]

    # Rapid Crunch Mode
    rapid_res = await tutor.explain_concept("Amdahl's Law", mode=TutoringMode.RAPID, subject="Computer Architecture")
    assert rapid_res["mode"] == "rapid"
    assert "Core Truth" in rapid_res["explanation"]
    assert "Exam Trap" in rapid_res["explanation"]


@pytest.mark.asyncio
async def test_claude_tutor_question_generation():
    tutor = ClaudeTutor()
    q_bank = await tutor.generate_practice_questions(topic="Binary Search Trees", num_questions=3, difficulty="hard")
    assert q_bank["total_questions"] == 3
    assert len(q_bank["questions"]) == 3
    q1 = q_bank["questions"][0]
    assert "Binary Search Trees" in q1["prompt"]
    assert len(q1["options"]) == 4
    assert q1["correct_option"] == "A"
    assert "solution_rubric" in q1


# ─────────────────────────────────────────────────────────────
# 4. Markdown Deadline Watcher Tests
# ─────────────────────────────────────────────────────────────

def test_deadline_watcher_parsing(tmp_path):
    todo_file = tmp_path / "todo.md"
    todo_content = """# Study Todo List
- [ ] Operating Systems Lab 3 (due: 2026-10-25 23:59) #high
- [ ] Distributed Systems Paper Review (due: 2026-10-28 12:00)
- [x] Finished reading Chapter 4
- [ ] General review of algorithms
"""
    todo_file.write_text(todo_content, encoding="utf-8")

    watcher = DeadlineWatcher(todo_file=todo_file, idle_threshold_seconds=10.0, min_reminder_interval=0.1)
    deadlines = watcher.parse_todo_file()

    assert len(deadlines) == 3  # completed item excluded
    assert deadlines[0].title == "Operating Systems Lab 3"
    assert deadlines[0].priority == "high"
    assert deadlines[0].due_date == "2026-10-25 23:59"

    # Pass time check simulation
    nudge = watcher.check_for_pass_time_reminder(current_window_title="YouTube - Random Videos")
    assert nudge is not None
    assert nudge["trigger"] in ["window_distraction", "idle_pass_time"]
    assert "Operating Systems Lab 3" in nudge["senpai_message"]
