import unittest
import json
from app import app
from models import get_db_connection


class TestCupAvailabilityFeature(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Reset settings for testing
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE settings SET setting_value = TRUE WHERE setting_key = 'small_cups_available'"
        )
        cursor.execute(
            "UPDATE settings SET setting_value = TRUE WHERE setting_key = 'large_cups_available'"
        )
        conn.commit()
        conn.close()

    def test_get_cup_availability(self):
        """Test getting cup availability settings"""
        response = self.app.get("/api/settings/cups")
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("small_cups_available", data)
        self.assertIn("large_cups_available", data)

    def test_update_cup_availability(self):
        """Test updating cup availability settings"""
        # Login as admin first
        with self.app.session_transaction() as session:
            session["admin_id"] = 1  # Mock admin login

        # Update settings
        test_settings = {"small_cups_available": False, "large_cups_available": True}

        response = self.app.post(
            "/api/settings/cups",
            data=json.dumps(test_settings),
            content_type="application/json",
        )

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])

        # Verify settings were updated
        response = self.app.get("/api/settings/cups")
        data = json.loads(response.data)
        self.assertEqual(data["small_cups_available"], False)
        self.assertEqual(data["large_cups_available"], True)

    def test_update_without_auth(self):
        """Test updating cup availability without admin authentication"""
        # No login

        test_settings = {"small_cups_available": False}

        response = self.app.post(
            "/api/settings/cups",
            data=json.dumps(test_settings),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)  # Should be unauthorized


if __name__ == "__main__":
    unittest.main()
