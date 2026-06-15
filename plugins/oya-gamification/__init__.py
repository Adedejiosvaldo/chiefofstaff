import os
import sys
import random
from datetime import datetime

# Add parent plugins directory so we can import the shared DB module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chief_of_staff_db

# Hardcoded technical trivia pool for daily challenges
TRIVIA_POOL = [
    {
        "id": 1,
        "question": "Which HTTP status code represents 'Teapot'?",
        "options": ["A) 404", "B) 418", "C) 502", "D) 400"],
        "correct": "B"
    },
    {
        "id": 2,
        "question": "In Python, which keyword is used to handle concurrent routines as tasks using async/await?",
        "options": ["A) asyncio", "B) multiprocessing", "C) threading", "D) concurrent.futures"],
        "correct": "A"
    },
    {
        "id": 3,
        "question": "Which SQLite journal mode writes transactions to a separate file first before updating the main database, enabling high concurrency?",
        "options": ["A) DELETE", "B) TRUNCATE", "C) MEMORY", "D) WAL"],
        "correct": "D"
    },
    {
        "id": 4,
        "question": "Which of the following database isolation levels guarantees that a transaction will read only committed data and that no other transaction can modify the data read by this transaction until it completes?",
        "options": ["A) Read Uncommitted", "B) Read Committed", "C) Repeatable Read", "D) Serializable"],
        "correct": "C"
    },
    {
        "id": 5,
        "question": "What does the 'C' stand for in CAP Theorem?",
        "options": ["A) Consistency", "B) Concurrency", "C) Complexity", "D) Capacity"],
        "correct": "A"
    },
    {
        "id": 6,
        "question": "Which tool in the Docker suite is used to define and run multi-container Docker applications?",
        "options": ["A) Docker Swarm", "B) Docker Compose", "C) Docker Machine", "D) Docker Kubernetes"],
        "correct": "B"
    }
]

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

def _get_gamification_status_tool() -> str:
    """Returns a beautifully formatted summary card of the user's gamification stats."""
    try:
        stats = chief_of_staff_db.get_gamification_stats()
        xp = stats.get("xp", 0)
        level = stats.get("level", 1)
        freezes = stats.get("streak_freezes", 2)
        hearts = stats.get("hearts", 5)
        
        # Calculate level progress
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

def _record_habit_resolution_tool(habit_name: str, outcome: str, is_late: bool = False, reason: str = None) -> dict:
    """
    Evaluates and records the outcome of a habit check-in, applying XP and streak logic.
    
    Args:
        habit_name (str): Name of the habit.
        outcome (str): One of: 'done', 'deferred', 'excused', 'missed'.
        is_late (bool): True if completed late.
        reason (str): Optional context / excuse.
    """
    try:
        stats = chief_of_staff_db.get_gamification_stats()
        current_hearts = stats.get("hearts", 5)
        current_freezes = stats.get("streak_freezes", 2)
        current_xp = stats.get("xp", 0)
        current_level = stats.get("level", 1)
        
        # Lockout check: if 0 hearts and they are missing a task, enforce penalty state
        if current_hearts <= 0 and outcome == "missed":
            return {
                "success": False,
                "msg": "🚨 **PENALTY STATE ACTIVE!** You have 0 Hearts remaining. You must answer a technical trivia question correctly or perform a deep-work sprint to recover a heart before you can log further missed goals."
            }
            
        habit = chief_of_staff_db.get_habit_streak(habit_name)
        current_streak = habit.get("streak", 0)
        best_streak = habit.get("best_streak", 0)
        total_completions = habit.get("total_completions", 0)
        
        # Output info variables
        xp_gain = 0
        dice_roll = 0
        dice_bonus = 0
        level_up = False
        freeze_spent = False
        milestone = None
        new_badge = None
        
        # Log to general habits table
        conn = chief_of_staff_db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO habits (habit_name, status) VALUES (?, ?)",
            (habit_name, "completed" if outcome == "done" else outcome)
        )
        conn.commit()
        conn.close()
        
        if outcome == "done":
            # 1. Base XP
            base_xp = 5 if is_late else 10
            xp_gain += base_xp
            
            # 2. Dice roll for variable reward (if on time)
            if not is_late:
                dice_roll = random.randint(1, 6)
                if dice_roll == 6:
                    dice_bonus = 20
                elif dice_roll == 5:
                    dice_bonus = 10
                xp_gain += dice_bonus
                
            # 3. Increment streaks
            current_streak += 1
            best_streak = max(best_streak, current_streak)
            total_completions += 1
            
            # 4. Check for milestones
            if current_streak in [3, 7, 14, 30, 60, 100]:
                milestone = current_streak
                
            # 5. Check for badge unlock
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
                if chief_of_staff_db.unlock_achievement(potential_badge):
                    new_badge = potential_badge
                    
            # 6. Apply XP and recalculate level
            new_xp = current_xp + xp_gain
            new_level = _get_level_for_xp(new_xp)
            if new_level > current_level:
                level_up = True
                current_freezes = min(5, current_freezes + 1)
                
                # Check level badge
                if new_level == 5 and "⚡ Powered Up" not in unlocked_badges:
                    if chief_of_staff_db.unlock_achievement("⚡ Powered Up"):
                        new_badge = "⚡ Powered Up"
                        
            chief_of_staff_db.update_gamification_stats(
                xp=new_xp, level=new_level, streak_freezes=current_freezes
            )
            chief_of_staff_db.update_habit_streak(
                habit_name, current_streak, best_streak, total_completions
            )
            
            # Formulate detailed response payload
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
            
        elif outcome == "deferred" or outcome == "excused":
            # Deferrals/excuses hold the streak and do not impact XP/hearts
            return {
                "success": True,
                "outcome": outcome,
                "new_streak": current_streak
            }
            
        elif outcome == "missed":
            # 1. Check streak freeze protection
            if current_streak >= 3 and current_freezes > 0:
                current_freezes -= 1
                freeze_spent = True
                # Streak is held, not reset
            else:
                current_streak = 0
                
            # 2. Lose a heart
            current_hearts = max(0, current_hearts - 1)
            
            # 3. Save updates
            chief_of_staff_db.update_gamification_stats(
                streak_freezes=current_freezes, hearts=current_hearts
            )
            chief_of_staff_db.update_habit_streak(
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

def _get_daily_trivia_tool() -> dict:
    """Returns a random micro-quiz from the pool to let the user recover a heart or save their streak."""
    q = random.choice(TRIVIA_POOL)
    return {
        "success": True,
        "question_id": q["id"],
        "question": q["question"],
        "options": q["options"]
    }

def _submit_trivia_answer_tool(question_id: int, answer: str) -> dict:
    """Checks the trivia answer and updates user stats on success."""
    try:
        q = next((item for item in TRIVIA_POOL if item["id"] == question_id), None)
        if not q:
            return {"success": False, "msg": "Invalid question ID."}
            
        cleaned_answer = answer.strip().upper()
        if cleaned_answer == q["correct"] or cleaned_answer in q["correct"]:
            # Correct answer! Recover a heart (cap at 5)
            stats = chief_of_staff_db.get_gamification_stats()
            current_hearts = min(5, stats.get("hearts", 5) + 1)
            chief_of_staff_db.update_gamification_stats(hearts=current_hearts)
            
            return {
                "success": True,
                "correct": True,
                "msg": f"🎉 **Correct answer!** Heart recovered! You are now back to 💖 **{current_hearts} / 5 Hearts**."
            }
        else:
            return {
                "success": True,
                "correct": False,
                "msg": f"❌ **Incorrect.** The correct answer was **{q['correct']}**. Duo is disappointed. Streak remains at risk."
            }
    except Exception as e:
        return {"success": False, "msg": f"Error submitting answer: {str(e)}"}


def register(ctx):
    """Register the oya-gamification tools with Hermes Agent context."""
    ctx.register_tool(
        name="get_gamification_status",
        schema={
            "type": "object",
            "properties": {}
        },
        handler=lambda args: _get_gamification_status_tool()
    )
    
    ctx.register_tool(
        name="record_habit_resolution",
        schema={
            "type": "object",
            "properties": {
                "habit_name": {"type": "string", "description": "The description/name of the habit or task being resolved."},
                "outcome": {"type": "string", "enum": ["done", "deferred", "excused", "missed"], "description": "The resolution route."},
                "is_late": {"type": "boolean", "description": "True if the task is completed late, False otherwise. Defaults to False."},
                "reason": {"type": "string", "description": "User excuse or reschedule time."}
            },
            "required": ["habit_name", "outcome"]
        },
        handler=lambda args: _record_habit_resolution_tool(
            habit_name=args["habit_name"],
            outcome=args["outcome"],
            is_late=args.get("is_late", False),
            reason=args.get("reason")
        )
    )
    
    ctx.register_tool(
        name="get_daily_trivia",
        schema={
            "type": "object",
            "properties": {}
        },
        handler=lambda args: _get_daily_trivia_tool()
    )
    
    ctx.register_tool(
        name="submit_trivia_answer",
        schema={
            "type": "object",
            "properties": {
                "question_id": {"type": "integer", "description": "The ID of the trivia question answered."},
                "answer": {"type": "string", "description": "The chosen option letter (A, B, C, D)."}
            },
            "required": ["question_id", "answer"]
        },
        handler=lambda args: _submit_trivia_answer_tool(
            question_id=args["question_id"],
            answer=args["answer"]
        )
    )
