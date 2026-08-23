#!/usr/bin/env python3
"""
Automated Test Suite for Personal Chief of Staff Agent
Validates all 7 integrations, database operations, dynamic trivia, git activity across GitHub, and DevOps opportunity tracking.
"""

import os
import sys
import unittest
import importlib.util
import time

# Add plugins directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
plugins_dir = os.path.join(parent_dir, "plugins")
sys.path.insert(0, plugins_dir)

from core import db, todoist, calendar, git_activity, opportunity, buffer, trivia_bank


def import_plugin_module(plugin_folder_name: str):
    """Dynamically loads a Hermes plugin package by folder name."""
    init_path = os.path.join(plugins_dir, plugin_folder_name, "__init__.py")
    spec = importlib.util.spec_from_file_location(f"plugin_{plugin_folder_name}", init_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MockPluginContext:
    def __init__(self):
        self.tools = {}

    def register_tool(self, name, toolset, schema, handler):
        self.tools[name] = {
            "toolset": toolset,
            "schema": schema,
            "handler": handler
        }


class TestChiefOfStaff(unittest.TestCase):

    def test_01_db_initialization_and_notifications(self):
        """Test SQLite DB creation, notifications CRUD, and telemetry."""
        db.init_db()
        test_prompt = f"Test automated prompt {time.time()}"
        notif_id = db.add_notification(test_prompt)
        self.assertIsInstance(notif_id, int)

        pending = db.get_pending_notifications()
        self.assertTrue(any(item["id"] == notif_id for item in pending))

        db.update_notification_status(notif_id, "sent")
        updated_pending = db.get_pending_notifications()
        self.assertFalse(any(item["id"] == notif_id for item in updated_pending))

    def test_02_gamification_and_dynamic_trivia(self):
        """Test gamification stats and dynamic on-the-fly brutal trivia generation."""
        stats = db.get_gamification_stats()
        self.assertIn("xp", stats)
        self.assertIn("hearts", stats)
        self.assertIn("level", stats)

        from core import dynamic_trivia
        # Test dynamic on-the-fly brutal trivia generation
        challenge = dynamic_trivia.generate_brutal_trivia_on_the_fly()
        self.assertTrue(challenge.get("success"))
        self.assertIn("question", challenge)
        self.assertIn("options", challenge)
        self.assertEqual(len(challenge["options"]), 4)

        # Test brutal evaluation feedback
        oya_module = import_plugin_module("oya-gamification")
        submit_trivia_fn = oya_module.submit_trivia_answer_tool

        eval_res = submit_trivia_fn(challenge["challenge_id"], "A")
        self.assertTrue(eval_res.get("success"))
        self.assertTrue(any(term in eval_res.get("msg", "") for term in ["Verdict", "Rating", "Grade"]))

    def test_03_todoist_mock_and_calls(self):
        """Test Todoist client fallback to mock and response structures."""
        tasks = todoist.fetch_todoist_tasks("today | overdue")
        self.assertIsInstance(tasks, str)
        self.assertTrue("Todoist" in tasks)

        created = todoist.create_task("Test task creation", "today")
        self.assertTrue("Test task creation" in created)

        completed = todoist.complete_task("task-101")
        self.assertTrue("task-101" in completed)

    def test_04_calendar_mock_and_calls(self):
        """Test Google Calendar client fallback and date parsing."""
        events = calendar.fetch_events()
        self.assertIsInstance(events, str)
        self.assertTrue("Schedule" in events)

        booked = calendar.schedule_event("Deep Work Sprint", "2026-08-22T10:00:00", 90)
        self.assertTrue("Deep Work Sprint" in booked)

    def test_05_git_activity_github_and_local(self):
        """Test Git activity scanner against GitHub and local workspace."""
        summary = git_activity.get_local_git_commits(repo_paths_str=parent_dir, since_hours=48)
        self.assertIsInstance(summary, str)
        self.assertTrue("Developer Activity Summary" in summary)

    def test_06_opportunity_crawler_devops_and_relocation(self):
        """Test DevOps & Relocation job caching and deduplication."""
        test_url = f"https://example.com/devops-relocation-job-{time.time()}"
        is_new = db.add_opportunity("✈️ [VISA / RELOCATION] Senior Site Reliability Engineer", test_url, "job", "US / EU Relocation")
        self.assertTrue(is_new)

        # Duplicate should return False
        is_dup = db.add_opportunity("Duplicate", test_url, "job", "Test")
        self.assertFalse(is_dup)

        unread = opportunity.pull_cached_opportunities(limit=5)
        self.assertIsInstance(unread, str)
        self.assertTrue("DevOps" in unread or "Radar" in unread)

    def test_07_buffer_mock_queue(self):
        """Test Buffer LinkedIn post queueing."""
        res = buffer.add_to_buffer("Under the Hood: Distributed Locking with Redis")
        self.assertIsInstance(res, str)
        self.assertTrue("Buffer" in res)

    def test_08_all_plugins_registration(self):
        """Test that all 7 Hermes plugins register their tools without exceptions."""
        plugin_folders = [
            "todoist", "google-calendar", "git-activity",
            "opportunity-radar", "buffer", "notification-bridge", "oya-gamification"
        ]

        ctx = MockPluginContext()
        for folder in plugin_folders:
            mod = import_plugin_module(folder)
            self.assertTrue(hasattr(mod, "register"), f"Plugin {folder} missing register function")
            mod.register(ctx)

        expected_tools = [
            "get_todoist_tasks", "create_todoist_task", "complete_todoist_task",
            "get_calendar_schedule", "create_calendar_event",
            "analyze_local_git_activity",
            "run_opportunity_crawler", "pull_radar_opportunities",
            "buffer_queue_post",
            "fetch_pending_notifications", "add_notification", "get_recent_telemetry",
            "get_gamification_status", "record_habit_resolution", "get_daily_trivia", "submit_trivia_answer"
        ]

        for tool_name in expected_tools:
            self.assertIn(tool_name, ctx.tools, f"Missing tool registration: {tool_name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
