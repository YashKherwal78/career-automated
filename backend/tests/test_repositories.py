import unittest
import sqlite3
import os
import src.api.db
from src.core.repositories.manager import RepositoryManager

class TestRepositories(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_repo.db"
        src.api.db.DATABASE_PATH = self.db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE registry_lever (company_id TEXT, company_name TEXT, endpoint TEXT, priority INT, created_at REAL, updated_at REAL)")
        conn.execute("INSERT INTO registry_lever VALUES ('comp1', 'Company 1', 'endpoint', 1, 0, 0)")
        conn.commit()
        conn.close()
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_migration_repository(self):
        repos = RepositoryManager(self.db_path)
        
        with repos.transaction():
            self.assertEqual(repos.migration.get_current_version(), 0)
            repos.migration.record_migration(1, "init", True)
            self.assertEqual(repos.migration.get_current_version(), 1)
            self.assertTrue(repos.migration.is_compatible(1))
            self.assertFalse(repos.migration.is_compatible(2))
            
    def test_company_repository(self):
        repos = RepositoryManager(self.db_path)
        
        with repos.transaction():
            comp = repos.company.get_company("lever", "comp1")
            self.assertIsNotNone(comp)
            self.assertEqual(comp["company_id"], "comp1")
            
            comp_none = repos.company.get_company("lever", "comp2")
            self.assertIsNone(comp_none)
            
    def test_transaction_rollback(self):
        repos = RepositoryManager(self.db_path)
        
        try:
            with repos.transaction():
                repos.migration.record_migration(2, "fail_test", True)
                raise ValueError("Rollback!")
        except ValueError:
            pass
            
        with repos.transaction():
            self.assertEqual(repos.migration.get_current_version(), 0)

if __name__ == '__main__':
    unittest.main()
