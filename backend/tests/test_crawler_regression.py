import unittest
import sqlite3
from src.core.repositories.company.state import CompanyStateRepository
from src.discovery.connectors.bootstrap import bootstrap_connectors
from src.discovery.registry.connector_registry import ConnectorRegistry

class TestCrawlerRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bootstrap_connectors()
        cls.repo = CompanyStateRepository()

    def test_schema_adaptive_columns_exist(self):
        conn = sqlite3.connect('data/crm.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ats_registry)")
        cols = [r[1] for r in cursor.fetchall()]
        conn.close()

        required = ['next_check_at_tz', 'reserved_until_tz', 'lease_token', 'lease_epoch', 'crawl_tier']
        for col in required:
            self.assertIn(col, cols, f"Missing required adaptive column {col} in ats_registry")

    def test_all_27_providers_registered(self):
        conn = sqlite3.connect('data/crm.db')
        cursor = conn.cursor()
        cursor.execute("SELECT provider_id FROM ats_providers WHERE enabled = 1")
        providers = [r[0] for r in cursor.fetchall()]
        conn.close()

        self.assertGreaterEqual(len(providers), 27, "Expected at least 27 enabled providers in ats_providers")
        
        missing = []
        for p in providers:
            if p == 'infojobs_es':
                continue
            if ConnectorRegistry.get(p) is None:
                missing.append(p)
        self.assertEqual(missing, [], f"Providers missing connector resolution: {missing}")

    def test_reservation_and_lease_fencing(self):
        reserved = self.repo.reserve_due_board("regression-test-worker", lock_duration=300)
        self.assertIsNotNone(reserved, "Failed to reserve due board from ats_registry")
        self.assertIn("reservation_token", reserved)
        self.assertIn("company_id", reserved)

if __name__ == "__main__":
    unittest.main()
