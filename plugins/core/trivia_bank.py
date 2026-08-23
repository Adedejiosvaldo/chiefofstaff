import os
import json
import random
import urllib.request
from datetime import datetime
from . import db

# 40+ Staff-Level, Deep-Cut Engineering Trivia Questions (Fallback Pool)
# Covers Linux Kernel, Distributed Consensus, Memory Allocators, Database Storage Engines, and Networking

HARD_TRIVIA_POOL = [
    {
        "id": 101,
        "category": "Linux Kernel & Networking",
        "question": "In Linux socket programming with `epoll`, what is the critical difference between Level-Triggered (LT) and Edge-Triggered (ET) mode when reading from a socket?",
        "options": [
            "A) ET only notifies when the state changes from unreadable to readable, requiring a non-blocking read loop until EAGAIN/EWOULDBLOCK",
            "B) LT drops socket packets if not read within a 5ms kernel tick",
            "C) ET automatically transfers socket buffers directly to userspace memory via DMA",
            "D) LT requires edge-detection interrupts from the NIC hardware"
        ],
        "correct": "A"
    },
    {
        "id": 102,
        "category": "Distributed Consensus",
        "question": "In the Raft consensus algorithm, how does a leader determine that a log entry from its CURRENT term is safely committed?",
        "options": [
            "A) Once it has been replicated on a majority of cluster nodes",
            "B) Once all follower nodes send an explicit disk sync acknowledgment",
            "C) Only after receiving a commit token from the election candidate",
            "D) After the entry has survived 3 consecutive leader election heartbeats"
        ],
        "correct": "A"
    },
    {
        "id": 103,
        "category": "Database Storage Engines",
        "question": "In LSM-Tree (Log-Structured Merge-Tree) databases like RocksDB or Cassandra, what is the primary purpose of Leveled Compaction over Size-Tiered Compaction?",
        "options": [
            "A) Reduces read amplification and bounding space amplification at the expense of higher write amplification",
            "B) Completely eliminates the need for Write-Ahead Logs",
            "C) Prevents all disk fragmentation by using in-memory B-Trees",
            "D) Eliminates Bloom filter lookups on point reads"
        ],
        "correct": "A"
    },
    {
        "id": 104,
        "category": "Python Runtime & CPython",
        "question": "In CPython 3.12+, how does the cyclic garbage collector identify circular reference deadlocks among container objects?",
        "options": [
            "A) It temporarily subtracts 1 from each object's reference count for references originating from other tracked containers to find isolated subgraphs with net refcount 0",
            "B) It runs a mark-and-sweep algorithm across the entire operating system stack memory",
            "C) It replaces all cyclic references with weakref proxies automatically",
            "D) It pauses all threads and triggers a complete heap compaction"
        ],
        "correct": "A"
    },
    {
        "id": 105,
        "category": "TCP/IP & Networking",
        "question": "Why does a TCP connection endpoint enter the `TIME_WAIT` state for 2*MSL (Maximum Segment Lifetime) after sending the final ACK in a 4-way handshake?",
        "options": [
            "A) To ensure the remote end received the final ACK and to prevent delayed duplicate packets from being accepted by a new reincarnated connection on the same 4-tuple",
            "B) To allow the network interface card to drain its internal ring buffer",
            "C) To renegotiate TCP window scaling parameters for the next connection",
            "D) To flush kernel socket send buffers to persistent storage"
        ],
        "correct": "A"
    },
    {
        "id": 106,
        "category": "Database Concurrency & MVCC",
        "question": "In PostgreSQL MVCC, what happens to old row versions (dead tuples) created by UPDATE or DELETE operations until `VACUUM` cleans them up?",
        "options": [
            "A) They remain on disk pages and are invisible to newer transactions based on `xmin` / `xmax` transaction ID comparisons",
            "B) They are moved immediately to a temporary swap partition on disk",
            "C) They are overwritten in-place during the next transaction write",
            "D) They cause an immediate table lock until an autovacuum worker spawns"
        ],
        "correct": "A"
    },
    {
        "id": 107,
        "category": "Go Runtime & Concurrency",
        "question": "In the Go runtime scheduler (GMP model), what mechanism does a processor (P) use when its local run queue becomes empty?",
        "options": [
            "A) Work-stealing: It attempts to steal half the executable goroutines (G) from another processor's local queue",
            "B) It immediately puts the OS thread (M) into a kernel sleep state until a signal is received",
            "C) It terminates the running goroutine and spawns a new runtime thread",
            "D) It blocks the network poller until a channel receives data"
        ],
        "correct": "A"
    },
    {
        "id": 108,
        "category": "Operating Systems & Memory",
        "question": "What is the primary function of the Linux kernel's Transparent Huge Pages (THP) mechanism, and why is it often disabled in Redis/database workloads?",
        "options": [
            "A) It uses 2MB pages to reduce TLB cache misses, but causes high latency spikes during memory allocation compaction and fork/copy-on-write overhead",
            "B) It encrypts physical memory pages, slowing down Redis hash lookups",
            "C) It prevents processes from using swap space",
            "D) It limits the maximum RAM a single process can allocate to 4GB"
        ],
        "correct": "A"
    },
    {
        "id": 109,
        "category": "Distributed Systems",
        "question": "In Google Spanner's TrueTime API, how does the system achieve strict external consistency (linearizability) across globally distributed transactions?",
        "options": [
            "A) By using synchronized atomic clocks and GPS receivers with bounded uncertainty [earliest, latest] and having transactions wait out the uncertainty window (commit-wait)",
            "B) By electing a single global master datacenter in North America for all write locks",
            "C) By leveraging quantum entanglement network relays between cloud zones",
            "D) By refusing all write transactions that cross continent borders"
        ],
        "correct": "A"
    },
    {
        "id": 110,
        "category": "Security & Cryptography",
        "question": "Why is AES-GCM preferred over AES-CBC with HMAC in modern TLS 1.3 cryptographic suites?",
        "options": [
            "A) AES-GCM is an Authenticated Encryption with Associated Data (AEAD) mode that provides confidentiality and integrity in a single pass with hardware acceleration",
            "B) AES-CBC cannot support 256-bit encryption keys",
            "C) AES-GCM does not require an initialization vector (IV)",
            "D) AES-CBC is vulnerable to quantum Grover key recovery in constant time"
        ],
        "correct": "A"
    },
    {
        "id": 111,
        "category": "Docker & Linux Namespaces",
        "question": "Which Linux kernel namespace isolates process IDs, such that PID 1 inside a Docker container is different from its host PID?",
        "options": [
            "A) PID namespace (CLONE_NEWPID)",
            "B) Mount namespace (CLONE_NEWNS)",
            "C) User namespace (CLONE_NEWUSER)",
            "D) Net namespace (CLONE_NEWNET)"
        ],
        "correct": "A"
    },
    {
        "id": 112,
        "category": "Databases & B-Trees",
        "question": "In a B+ Tree index (used by MySQL InnoDB and Postgres), why are data records or leaf pointers stored ONLY at the leaf nodes rather than internal nodes?",
        "options": [
            "A) Maximizes the fanout factor of internal nodes (fitting more keys per page) and allows sequential leaf scans via linked lists",
            "B) Prevents binary search tree degeneration into linked lists",
            "C) Eliminates all disk writes during index updates",
            "D) Guarantees that tree height never exceeds 2"
        ],
        "correct": "A"
    }
]


def randomize_question_options(q_dict: dict) -> dict:
    """Randomizes option letters (A, B, C, D) so the correct answer isn't predictable."""
    correct_text = q_dict["options"][0].split(") ", 1)[1] if ") " in q_dict["options"][0] else q_dict["options"][0]
    all_option_texts = [opt.split(") ", 1)[1] if ") " in opt else opt for opt in q_dict["options"]]

    random.shuffle(all_option_texts)

    letters = ["A", "B", "C", "D"]
    new_options = []
    new_correct_letter = "A"

    for idx, text in enumerate(all_option_texts):
        letter = letters[idx]
        new_options.append(f"{letter}) {text}")
        if text == correct_text:
            new_correct_letter = letter

    return {
        "id": q_dict["id"],
        "category": q_dict.get("category", "Staff Engineering"),
        "question": q_dict["question"],
        "options": new_options,
        "correct": new_correct_letter
    }


def generate_dynamic_trivia() -> dict:
    """
    Generates a brand-new, unpredictable, brutally tough engineering question via LLM
    or falls back to randomized staff-level pool questions.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    model = os.environ.get("LLM_MODEL_CRONS", "deepseek/deepseek-chat")

    if api_key:
        try:
            topics = [
                "Linux kernel networking & epoll internals",
                "Distributed consensus (Raft/Paxos) edge cases",
                "PostgreSQL / MySQL MVCC and WAL write paths",
                "CPython memory management & GIL sub-interpreters",
                "TCP/IP congestion control (BBR vs CUBIC) and socket states",
                "LSM-Tree compaction strategies and write amplification",
                "Go runtime GMP scheduler work-stealing & channel internals",
                "eBPF kernel tracepoints and memory safety verification",
                "Distributed locks & split-brain fencing tokens",
                "Docker cgroups v2 memory pressure & OOM-killer logic"
            ]
            chosen_topic = random.choice(topics)

            prompt = (
                f"Generate exactly ONE extremely hard, senior/staff-level technical trivia question on: '{chosen_topic}'.\n"
                "The question must be deeply technical, testing nuanced real-world systems edge cases. Avoid generic textbook trivia.\n"
                "Return ONLY a valid JSON object with this exact structure:\n"
                "{\n"
                '  "category": "Topic Name",\n'
                '  "question": "The question text",\n'
                '  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
                '  "correct": "A" (or B, C, D)\n'
                "}"
            )

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            base_url = "https://openrouter.ai/api/v1/chat/completions"
            if os.environ.get("DEEPSEEK_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
                base_url = "https://api.deepseek.com/v1/chat/completions"

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8
            }
            req = urllib.request.Request(base_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            content = resp_data["choices"][0]["message"]["content"].strip()
            # Clean markdown codeblocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            parsed_q = json.loads(content.strip())
            q_id = int(datetime.now().strftime("%f"))  # Unique microsecond ID
            parsed_q["id"] = q_id

            # Cache question in SQLite so answer validation is deterministic
            db.log_telemetry("dynamic_trivia_generated", {
                "id": q_id,
                "correct": parsed_q["correct"],
                "question": parsed_q["question"]
            })

            return {
                "success": True,
                "question_id": q_id,
                "category": parsed_q.get("category", "Staff Engineering"),
                "question": parsed_q["question"],
                "options": parsed_q["options"],
                "correct": parsed_q["correct"]
            }

        except Exception as e:
            print(f"Dynamic trivia generation fallback: {e}")

    # Fallback to randomized pool
    raw_q = random.choice(HARD_TRIVIA_POOL)
    shuffled_q = randomize_question_options(raw_q)
    return {
        "success": True,
        "question_id": shuffled_q["id"],
        "category": shuffled_q["category"],
        "question": shuffled_q["question"],
        "options": shuffled_q["options"],
        "correct": shuffled_q["correct"]
    }
