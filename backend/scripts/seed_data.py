"""
Database Seeding Script for Trainer Progression App.

Populates initial development and testing records:
1. One personal trainer account (Coach Mike).
2. Two client profiles:
   - Sarah Miller (has left shoulder impingement injury on file).
   - David Chen (clean baseline, no injuries).
3. One active, unguessable cryptographic session UUID for Sarah Miller.
4. One approved initial workout plan for Sarah using canonical exercise vocabulary
   (ex_bench, ex_squat, ex_row).

Run with:
    python backend/scripts/seed_data.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.trainer import Trainer
from app.models.client import ClientProfile, ClientSession
from app.models.workout import WorkoutPlan


async def seed_database() -> None:
    print("🌱 Connecting to database to seed initial data...")

    async with async_session_factory() as session:
        # 1. Seed Trainer (Linked to real Supabase GoTrue User)
        trainer_email = "coach.mike@pursuit.org"
        stmt = select(Trainer).where(
            (Trainer.email == trainer_email) | (Trainer.email == "coach.mike@example.com")
        )
        res = await session.execute(stmt)
        trainer = res.scalar_one_or_none()

        real_supabase_uid = "2fff5919-654b-4c31-9aea-5c0e1d55215b"
        if not trainer:
            trainer = Trainer(
                supabase_user_id=real_supabase_uid,
                email=trainer_email,
                full_name="Coach Mike Henderson",
            )
            session.add(trainer)
            await session.flush()
            print(f"✅ Created Trainer: {trainer.full_name} ({trainer.email}) [ID: {trainer.id}]")
        else:
            trainer.supabase_user_id = real_supabase_uid
            trainer.email = trainer_email
            await session.flush()
            print(f"ℹ️ Trainer verified with live Supabase user: {trainer.full_name} [ID: {trainer.id}]")

        # 2. Seed Client 1: Sarah Miller (Active injury profile for Agent 2 safety testing)
        sarah_email = "sarah.miller@example.com"
        stmt = select(ClientProfile).where(ClientProfile.email == sarah_email)
        res = await session.execute(stmt)
        sarah = res.scalar_one_or_none()

        if not sarah:
            sarah = ClientProfile(
                trainer_id=trainer.id,
                full_name="Sarah Miller",
                email=sarah_email,
                phone="+1-555-0142",
                primary_goal="Strength",
                experience_level="Intermediate",
                injuries_json=["Left shoulder impingement (2025)"],
                intake_notes="Experienced lifter focusing on compound movements. Left shoulder impingement history; sensitive to heavy bench volume.",
            )
            session.add(sarah)
            await session.flush()
            print(f"✅ Created Client Profile: {sarah.full_name} [ID: {sarah.id}] (With Shoulder Impingement)")
        else:
            print(f"ℹ️ Client already exists: {sarah.full_name} [ID: {sarah.id}]")

        # 3. Seed Client 2: David Chen (Clean profile for standard progression testing)
        david_email = "david.chen@example.com"
        stmt = select(ClientProfile).where(ClientProfile.email == david_email)
        res = await session.execute(stmt)
        david = res.scalar_one_or_none()

        if not david:
            david = ClientProfile(
                trainer_id=trainer.id,
                full_name="David Chen",
                email=david_email,
                phone="+1-555-0189",
                primary_goal="Hypertrophy",
                experience_level="Beginner",
                injuries_json=[],
                intake_notes="New client, zero injuries. Focused on basic progressive overload.",
            )
            session.add(david)
            await session.flush()
            print(f"✅ Created Client Profile: {david.full_name} [ID: {david.id}] (No Injuries)")
        else:
            print(f"ℹ️ Client already exists: {david.full_name} [ID: {david.id}]")

        # 4. Generate Active Cryptographic Session Token for Sarah Miller
        session_token = str(uuid.uuid4())
        client_session = ClientSession(
            client_id=sarah.id,
            session_token=session_token,
            is_active=True,
            last_accessed_at=datetime.utcnow(),
        )
        session.add(client_session)
        await session.flush()
        print(f"✅ Generated Session Token for Sarah: {session_token}")

        # 5. Seed Approved Initial Workout Plan for Sarah using canonical exercise vocabulary
        plan_stmt = (
            select(WorkoutPlan)
            .where(WorkoutPlan.client_id == sarah.id, WorkoutPlan.status == "approved")
        )
        plan_res = await session.execute(plan_stmt)
        active_plan = plan_res.scalar_one_or_none()

        if not active_plan:
            active_plan = WorkoutPlan(
                client_id=sarah.id,
                week_label="Week 1 - Baseline Progression",
                status="approved",
                exercises_json=[
                    {
                        "exercise_id": "ex_bench",
                        "name": "Barbell Bench Press",
                        "sets": 3,
                        "target_reps": 10,
                        "target_weight_lbs": 135.0,
                    },
                    {
                        "exercise_id": "ex_squat",
                        "name": "Back Squat",
                        "sets": 3,
                        "target_reps": 8,
                        "target_weight_lbs": 185.0,
                    },
                    {
                        "exercise_id": "ex_row",
                        "name": "Barbell Bent-Over Row",
                        "sets": 3,
                        "target_reps": 10,
                        "target_weight_lbs": 115.0,
                    },
                ],
                safety_flags_json=[],
                trainer_notes="Keep RPE around 7-8 for baseline week. Pay attention to left shoulder on bench press.",
                approved_at=datetime.utcnow(),
            )
            session.add(active_plan)
            await session.flush()
            print(f"✅ Created Approved Plan for Sarah: {active_plan.week_label} [ID: {active_plan.id}]")
        else:
            print(f"ℹ️ Active approved plan already exists for Sarah [ID: {active_plan.id}]")

        await session.commit()

    print("\n" + "=" * 60)
    print("🎉 SEED DATA INITIALIZATION COMPLETE!")
    print("=" * 60)
    print(f"Trainer Email:        {trainer_email}")
    print(f"Client 1:             Sarah Miller (ID: {sarah.id})")
    print(f"Client 2:             David Chen (ID: {david.id})")
    print(f"Sarah's Session UUID: {session_token}")
    print(f"Client Mobile URL:    http://localhost:3000/s/{session_token}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(seed_database())
