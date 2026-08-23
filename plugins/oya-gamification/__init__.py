import os
import sys
import random
import json
from datetime import datetime

# Import shared core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db
from core.dynamic_trivia import generate_brutal_trivia_on_the_fly, evaluate_user_trivia_answer


def _xp_threshold(level: int) -> int:
    return 50 * level * (level - 1)


def _get_level_for_xp(xp: int) -> int:
    level = 1
    while _xp_threshold(level + 1) <= xp:
        level += 1
    return level


def _generate_progress_bar(percentage: float, width: int = 10) -> str:
    filled = int(round(percentage * width))
    bar = "▓" * filled + "░" * (width - filled)
    return f"[{bar}]"


def get_gamification_status_tool() -> str:
    """Returns a beautifully formatted summary card of the user's gamification stats."""
    try:
        stats = db.get_gamification_stats()
        xp = stats.get("xp", 0)
        level = stats.get("level", 1)
        freezes = stats.get("streak_freezes", 2)
        hearts = stats.get("hearts", 5)

        current_threshold = _xp_threshold(level)
        next_threshold = _xp_threshold(level + 1)
        needed = next_threshold - current_threshold
        progress = xp - current_threshold
        percentage = min(1.0, max(0.0, progress / needed if needed > 0 else 0))
        bar = _generate_progress_bar(percentage)

        output = [
            f"📊 **Joseph's Accountability Stats**",
            f"⚡ **Level {level}**  ·  {xp} XP",
            f"{bar}  {needed - progress} XP left to Level {level+1}",
            f"",
            f"🔥 **Habit Streaks**:"
        ]

        streaks = stats.get("streaks", [])
        if not streaks:
            output.append("  · No active streaks yet. Let's build one! 🌱")
        else:
            for s in streaks[:6]:
                output.append(f"  · *{s['habit_name']}*: {s['streak']} 🔥  (best: {s['best_streak']})")

        output.append("")
        output.append(f"🧊 **{freezes} / 5 Freezes**  ·  💖 **{hearts} / 5 Hearts**")

        badges = stats.get("achievements", [])
        if badges:
            output.append(f"🏆 **Badges**: {', '.join(badges)}")

        return "\n".join(output)

    except Exception as e:
        return f"Error retrieving stats: {str(e)}"


def record_habit_resolution_tool(habit_name: str, outcome: str, is_late: bool = False, reason: str = None) -> dict:
    """
    Evaluates and records the outcome of a habit check-in, applying XP and streak logic.
    """
    try:
        stats = db.get_gamification_stats()
        current_hearts = stats.get("hearts", 5)
        current_freezes = stats.get("streak_freezes", 2)
        current_xp = stats.get("xp", 0)
        current_level = stats.get("level", 1)

        # Lockout check: if 0 hearts and they are missing a task, enforce penalty state
        if current_hearts <= 0 and outcome == "missed":
            return {
                "success": False,
                "msg": "🚨 **PENALTY STATE ACTIVE!** You have 0 Hearts remaining. You must answer an on-the-fly technical trivia challenge to recover a heart before logging further missed goals."
            }

        habit = db.get_habit_streak(habit_name)
        current_streak = habit.get("streak", 0)
        best_streak = habit.get("best_streak", 0)
        total_completions = habit.get("total_completions", 0)

        xp_gain = 0
        dice_roll = 0
        dice_bonus = 0
        level_up = False
        freeze_spent = False
        milestone = None
        new_badge = None

        db.log_habit_event(habit_name, "completed" if outcome == "done" else outcome)

        if outcome == "done":
            base_xp = 5 if is_late else 10
            xp_gain += base_xp

            if not is_late:
                dice_roll = random.randint(1, 6)
                if dice_roll == 6:
                    dice_bonus = 20
                elif dice_roll == 5:
                    dice_bonus = 10
                xp_gain += dice_bonus

            current_streak += 1
            best_streak = max(best_streak, current_streak)
            total_completions += 1

            if current_streak in [3, 7, 14, 30, 60, 100]:
                milestone = current_streak

            unlocked_badges = stats.get("achievements", [])
            potential_badge = None
            if total_completions == 1:
                potential_badge = "🌱 First Step"
            elif current_streak == 7:
                potential_badge = "🥉 Week One"
            elif current_streak == 14:
                potential_badge = "🥈 Fortnight"
            elif current_streak == 30:
                potential_badge = "🥇 Monthly"
            elif current_streak == 100:
                potential_badge = "💎 Century"

            if potential_badge and potential_badge not in unlocked_badges:
                if db.unlock_achievement(potential_badge):
                    new_badge = potential_badge

            new_xp = current_xp + xp_gain
            new_level = _get_level_for_xp(new_xp)
            if new_level > current_level:
                level_up = True
                current_freezes = min(5, current_freezes + 1)
                if new_level == 5 and "⚡ Powered Up" not in unlocked_badges:
                    if db.unlock_achievement("⚡ Powered Up"):
                        new_badge = "⚡ Powered Up"

            db.update_gamification_stats(
                xp=new_xp, level=new_level, streak_freezes=current_freezes
            )
            db.update_habit_streak(
                habit_name, current_streak, best_streak, total_completions
            )

            return {
                "success": True,
                "outcome": "done",
                "xp_gain": xp_gain,
                "dice_roll": dice_roll,
                "dice_bonus": dice_bonus,
                "new_streak": current_streak,
                "level_up": level_up,
                "new_level": new_level if level_up else current_level,
                "milestone": milestone,
                "new_badge": new_badge
            }

        elif outcome in ["deferred", "excused"]:
            return {
                "success": True,
                "outcome": outcome,
                "new_streak": current_streak
            }

        elif outcome == "missed":
            if current_streak >= 3 and current_freezes > 0:
                current_freezes -= 1
                freeze_spent = True
            else:
                current_streak = 0

            current_hearts = max(0, current_hearts - 1)

            db.update_gamification_stats(
                streak_freezes=current_freezes, hearts=current_hearts
            )
            db.update_habit_streak(
                habit_name, current_streak, best_streak, total_completions
            )

            return {
                "success": True,
                "outcome": "missed",
                "new_streak": current_streak,
                "freeze_spent": freeze_spent,
                "hearts_left": current_hearts
            }

        else:
            return {"success": False, "msg": f"Invalid outcome route: {outcome}"}

    except Exception as e:
        return {"success": False, "msg": f"Error recording outcome: {str(e)}"}


def get_daily_trivia_tool() -> dict:
    """Generates an on-the-fly, unpredictable, brutally hard technical challenge."""
    q_data = generate_brutal_trivia_on_the_fly()
    return {
        "success": True,
        "challenge_id": q_data["challenge_id"],
        "category": q_data["category"],
        "question": q_data["question"],
        "options": q_data["options"]
    }


def submit_trivia_answer_tool(challenge_id: int, answer: str) -> dict:
    """
    Evaluates the user's answer and provides a Staff Engineer Rating and technical critique.
    """
    result = evaluate_user_trivia_answer(challenge_id, answer)
    return {
        "success": True,
        "correct": result["correct"],
        "msg": result["feedback"]
    }


def register(ctx):
    """Register the oya-gamification tools with Hermes Agent context."""
    ctx.register_tool(
        name="get_gamification_status",
        toolset="oya-gamification",
        schema={"type": "object", "properties": {}},
        handler=lambda args, **kwargs: get_gamification_status_tool()
    )

    ctx.register_tool(
        name="record_habit_resolution",
        toolset="oya-gamification",
        schema={
            "type": "object",
            "properties": {
                "habit_name": {"type": "string", "description": "The name of the habit or task being resolved."},
                "outcome": {"type": "string", "enum": ["done", "deferred", "excused", "missed"], "description": "The resolution route."},
                "is_late": {"type": "boolean", "description": "True if completed late. Defaults to False."},
                "reason": {"type": "string", "description": "User reason or rescheduled time."}
            },
            "required": ["habit_name", "outcome"]
        },
        handler=lambda args, **kwargs: record_habit_resolution_tool(
            habit_name=args["habit_name"],
            outcome=args["outcome"],
            is_late=args.get("is_late", False),
            reason=args.get("reason")
        )
    )

    ctx.register_tool(
        name="get_daily_trivia",
        toolset="oya-gamification",
        schema={"type": "object", "properties": {}},
        handler=lambda args, **kwargs: get_daily_trivia_tool()
    )

    ctx.register_tool(
        name="submit_trivia_answer",
        toolset="oya-gamification",
        schema={
            "type": "object",
            "properties": {
                "challenge_id": {"type": "integer", "description": "The ID of the trivia challenge answered."},
                "answer": {"type": "string", "description": "The user answer (e.g. 'A', 'B', 'C', 'D')."}
            },
            "required": ["challenge_id", "answer"]
        },
        handler=lambda args, **kwargs: submit_trivia_answer_tool(
            challenge_id=args.get("challenge_id") or args.get("question_id", 1),
            answer=args["answer"]
        )
    )
