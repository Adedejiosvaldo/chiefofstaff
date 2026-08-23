import os
import json
import random
import urllib.request
from datetime import datetime
from . import db

BRUTAL_CATEGORIES = [
    {
        "category": "🧠 AI Engineering & LLM Systems",
        "focus": "Transformer KV-cache memory calculation, FlashAttention online softmax tiling, LoRA rank/alpha weight gradients, speculative decoding verification loops, HNSW vector graph connectivity, quantization scale/zero-point clipping"
    },
    {
        "category": "☁️ DevOps, SRE & Linux Kernel",
        "focus": "Linux epoll Edge-Triggered EAGAIN drains, cgroups v2 PSI (Pressure Stall Information) memory pressure metrics, eBPF BPF_MAP_TYPE_RINGBUF vs PERF_EVENT, TCP BBR congestion window pacing vs CUBIC loss, Kubernetes etcd consensus lease loss"
    },
    {
        "category": "⚙️ Distributed Systems & Database Engines",
        "focus": "LSM-tree Leveled vs Tiered compaction space/write amplification, PostgreSQL MVCC xmin/xmax tuple visibility during concurrent snapshot isolation, Raft leader lease split-brain invariants, Redis cluster hash slot migration edge cases, distributed 2PC coordinator failure states"
    }
]

# High-Difficulty Offline Fallback Bank
BRUTAL_FALLBACK_POOL = [
    {
        "category": "🧠 AI Engineering & LLM Systems",
        "question": "In FlashAttention (Dao et al.), how does the algorithm compute exact Multi-Head Attention without materializing the intermediate N x N attention matrix in slow GPU High Bandwidth Memory (HBM)?",
        "options": [
            "A) By tiling the Q, K, V blocks into GPU SRAM and incrementally maintaining scaling normalization factors via online softmax reformulation",
            "B) By converting all floating point weights to 4-bit integers before executing the matrix dot-product in tensor cores",
            "C) By pruning 80% of low-probability token connections using locality-sensitive hashing (LSH)",
            "D) By executing the attention computation asynchronously in CPU host memory via PCIe Gen 5"
        ],
        "correct": "A",
        "explanation": "FlashAttention tiles inputs across fast on-chip SRAM and uses an online softmax technique (keeping track of running row maximums and sum of exponentials) to avoid writing the O(N^2) attention score matrix to HBM."
    },
    {
        "category": "☁️ DevOps, SRE & Linux Kernel",
        "question": "In Linux cgroups v2, what does the `memory.pressure` file (PSI - Pressure Stall Information) specifically measure that raw `memory.current` usage metrics cannot capture?",
        "options": [
            "A) The percentage of CPU wall-clock time that tasks spent stalled waiting for memory reclaim, page cache thrashing, and swap I/O",
            "B) The physical temperature of the server's DDR5 RAM DIMMs",
            "C) The total number of unallocated byte pages remaining in the kernel slab allocator",
            "D) The network bandwidth consumed by remote NFS mounts"
        ],
        "correct": "A",
        "explanation": "PSI measures resource starvation and stalls. High memory usage isn't necessarily bad (page cache), but high PSI stall percentage means tasks are actively delayed waiting for memory reclamation or page-in I/O."
    },
    {
        "category": "⚙️ Distributed Systems & Database Engines",
        "question": "Under PostgreSQL's `REPEATABLE READ` transaction isolation level, what happens if Transaction A attempts to UPDATE a row that was already modified and committed by Transaction B AFTER Transaction A's snapshot was established?",
        "options": [
            "A) Transaction A immediately fails with a `could not serialize access due to concurrent update` error (First-Committer-Wins rule)",
            "B) Transaction A automatically waits for Transaction B's changes and applies its update silently on top",
            "C) Transaction A creates a duplicate phantom row with a new primary key",
            "D) The database crashes due to an unresolvable transaction ID wraparound"
        ],
        "correct": "A",
        "explanation": "In Postgres Repeatable Read (Snapshot Isolation), if a row updated by a concurrent transaction is modified, the current transaction cannot overwrite newer committed versions and must abort with a serialization error."
    }
]


def generate_brutal_trivia_on_the_fly() -> dict:
    """
    Dynamically generates a staff/principal-level engineering question on the fly
    via LLM (DeepSeek-V3 / OpenRouter), with fallback to curated deep-cut questions.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    model = os.environ.get("LLM_MODEL_CRONS", "deepseek/deepseek-chat")

    chosen_pillar = random.choice(BRUTAL_CATEGORIES)
    category = chosen_pillar["category"]
    focus_topics = chosen_pillar["focus"]

    if api_key:
        try:
            prompt = (
                f"You are a Principal Systems Architect designing a brutally hard technical challenge for a Senior/Staff Engineer.\n"
                f"Category: {category}\n"
                f"Specific Focus Areas: {focus_topics}\n\n"
                "RULES:\n"
                "1. Craft an original, unpredictable, deeply technical question testing real-world systems internals, edge cases, kernel flags, memory models, or distributed trade-offs.\n"
                "2. NO easy or generic textbook definitions. The distractors must sound plausible to a mid-level engineer but be technically flawed.\n"
                "3. Provide exactly 4 options (A, B, C, D) and randomly assign the correct answer.\n"
                "4. Return ONLY a valid JSON object matching this schema:\n"
                "{\n"
                f'  "category": "{category}",\n'
                '  "question": "The question text...",\n'
                '  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
                '  "correct": "A" (or B, C, D),\n'
                '  "explanation": "Deep technical explanation of the underlying mechanism..."\n'
                "}"
            )

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            base_url = "https://openrouter.ai/api/v1/chat/completions"
            if os.environ.get("DEEPSEEK_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
                base_url = "https://api.deepseek.com/v1/chat/completions"

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.85
            }
            req = urllib.request.Request(base_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            content = resp_data["choices"][0]["message"]["content"].strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            parsed = json.loads(content.strip())
            q_id = db.save_trivia_challenge(
                category=parsed.get("category", category),
                question=parsed["question"],
                options=parsed["options"],
                correct_option=parsed["correct"].strip().upper(),
                explanation=parsed.get("explanation", "")
            )

            return {
                "success": True,
                "challenge_id": q_id,
                "category": parsed.get("category", category),
                "question": parsed["question"],
                "options": parsed["options"]
            }

        except Exception as e:
            print(f"On-the-fly trivia generation error: {e}. Using brutal fallback.")

    # Fallback to local brutal pool
    fallback_q = random.choice(BRUTAL_FALLBACK_POOL)
    q_id = db.save_trivia_challenge(
        category=fallback_q["category"],
        question=fallback_q["question"],
        options=fallback_q["options"],
        correct_option=fallback_q["correct"],
        explanation=fallback_q["explanation"]
    )
    return {
        "success": True,
        "challenge_id": q_id,
        "category": fallback_q["category"],
        "question": fallback_q["question"],
        "options": fallback_q["options"]
    }


def evaluate_user_trivia_answer(challenge_id: int, user_answer_text: str) -> dict:
    """
    Brutally evaluates the user's answer, provides a Staff Engineer Rating,
    explains the exact underlying technical mechanics, and updates hearts in SQLite.
    """
    challenge = db.get_trivia_challenge(challenge_id)
    if not challenge:
        # Check if ID was from legacy pool
        return {
            "success": True,
            "correct": True,
            "feedback": "Challenge evaluated. Keep pushing your limits!"
        }

    correct_letter = challenge["correct_option"].strip().upper()
    cleaned_input = user_answer_text.strip().upper()

    is_correct = (
        cleaned_input == correct_letter
        or cleaned_input.startswith(correct_letter + ")")
        or cleaned_input.startswith(correct_letter + " ")
        or cleaned_input.startswith(correct_letter + ".")
    )

    explanation = challenge.get("explanation", "")
    category = challenge.get("category", "Systems Engineering")

    # Generate a brutal rating feedback
    if is_correct:
        stats = db.get_gamification_stats()
        new_hearts = min(5, stats.get("hearts", 5) + 1)
        db.update_gamification_stats(hearts=new_hearts)

        ratings = [
            "🏆 **Staff Engineer Rating: 9.8 / 10** · Masterful intuition for low-level systems!",
            "🔥 **Architect Grade: S-Tier** · Flawless comprehension of physical runtime constraints!",
            "⚡ **Principal Rating: 9.5 / 10** · You didn't fall for the trap. Exceptional depth!"
        ]
        chosen_rating = random.choice(ratings)

        feedback = (
            f"{chosen_rating}\n\n"
            f"✅ **Verdict**: Option **{correct_letter}** is correct.\n"
            f"💡 **Under the Hood**: {explanation}\n\n"
            f"💖 **Heart Recovered**: Back to **{new_hearts}/5 Hearts**. Streak is protected!"
        )
    else:
        critiques = [
            "💀 **Staff Rating: 2.5 / 10** · Junior misconception. Duo is in absolute disbelief.",
            "🚨 **Architect Grade: F** · You fell straight into the latency trap. In production, this brings down the cluster.",
            "⚠️ **Rating: 3.0 / 10** · That answer violates basic kernel invariants. Duo is judging you."
        ]
        chosen_critique = random.choice(critiques)

        feedback = (
            f"{chosen_critique}\n\n"
            f"❌ **Verdict**: You chose '{user_answer_text.strip()}'. The correct answer was **{correct_letter}**.\n"
            f"🔍 **Why You Failed**: {explanation}\n\n"
            f"💔 **No Heart Recovered**. Duo is watching. Complete an active task immediately to defend your streak!"
        )

    db.update_trivia_challenge_result(challenge_id, user_answer_text, is_correct, feedback)

    return {
        "success": True,
        "correct": is_correct,
        "feedback": feedback
    }
