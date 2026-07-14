import pytest
import sqlite3
from src.discovery.pipeline_state_manager import PipelineStateManager, TransitionError

@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # Setup schema
    conn.execute('''
        CREATE TABLE company_identities (
            company_id TEXT PRIMARY KEY,
            domain TEXT,
            canonical_name TEXT,
            website TEXT,
            aliases TEXT,
            lifecycle_state TEXT,
            health_state TEXT,
            failure_reason TEXT,
            crawl_status TEXT,
            verification_method TEXT,
            updated_at REAL
        )
    ''')
    conn.execute('''
        CREATE TABLE local_queues (
            _item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_name TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            status TEXT DEFAULT 'QUEUED',
            created_at REAL NOT NULL,
            locked_until REAL NOT NULL,
            retries INTEGER DEFAULT 0,
            UNIQUE(queue_name, payload_hash)
        )
    ''')
    conn.commit()
    return conn

def test_valid_canonical_transitions(test_db):
    company_id = "test-canonical-123"
    
    # 1. Insert bare company (no lifecycle state)
    test_db.execute("INSERT INTO company_identities (company_id) VALUES (?)", (company_id,))
    
    # 2. DISCOVERED -> VERIFICATION_PENDING -> VERIFYING -> VERIFIED -> CRAWL_PENDING -> CRAWLING -> ACTIVE
    PipelineStateManager.transition(company_id, "DISCOVERED", conn=test_db)
    
    row = test_db.execute("SELECT lifecycle_state FROM company_identities WHERE company_id = ?", (company_id,)).fetchone()
    assert row["lifecycle_state"] == "DISCOVERED"
    
    PipelineStateManager.transition(company_id, "VERIFICATION_PENDING", conn=test_db)
    PipelineStateManager.transition(company_id, "VERIFYING", conn=test_db)
    
    # Transition to VERIFIED and enqueue atomically
    PipelineStateManager.transition(company_id, "VERIFIED", queue_op={"queue_name": "crawl_queue", "payload": {"company_id": company_id}}, conn=test_db)
    
    # Check queue
    queue_row = test_db.execute("SELECT queue_name FROM local_queues WHERE queue_name = 'crawl_queue'").fetchone()
    assert queue_row["queue_name"] == "crawl_queue"
    
    PipelineStateManager.transition(company_id, "CRAWL_PENDING", conn=test_db)
    PipelineStateManager.transition(company_id, "CRAWLING", conn=test_db)
    
    # Transition to ACTIVE with crawl_status
    PipelineStateManager.transition(company_id, "ACTIVE", crawl_status="SUCCESS", conn=test_db)
    
    row = test_db.execute("SELECT lifecycle_state, crawl_status FROM company_identities WHERE company_id = ?", (company_id,)).fetchone()
    assert row["lifecycle_state"] == "ACTIVE"
    assert row["crawl_status"] == "SUCCESS"

def test_fast_path_transitions(test_db):
    company_id = "test-fastpath-123"
    test_db.execute("INSERT INTO company_identities (company_id) VALUES (?)", (company_id,))
    
    PipelineStateManager.transition(company_id, "DISCOVERED", conn=test_db)
    
    # Fast path directly transitions from DISCOVERED to VERIFIED with metadata
    PipelineStateManager.transition(
        company_id, 
        "VERIFIED", 
        verification_method="FAST_PATH", 
        queue_op={"queue_name": "crawl_queue", "payload": {"company_id": company_id}},
        conn=test_db
    )
    
    row = test_db.execute("SELECT lifecycle_state, verification_method FROM company_identities WHERE company_id = ?", (company_id,)).fetchone()
    assert row["lifecycle_state"] == "VERIFIED"
    assert row["verification_method"] == "FAST_PATH"

def test_invalid_transitions(test_db):
    company_id = "test-invalid-123"
    test_db.execute("INSERT INTO company_identities (company_id) VALUES (?)", (company_id,))
    PipelineStateManager.transition(company_id, "DISCOVERED", conn=test_db)
    
    # Try jumping directly to ACTIVE from DISCOVERED
    with pytest.raises(TransitionError, match="Illegal transition: DISCOVERED -> ACTIVE"):
        PipelineStateManager.transition(company_id, "ACTIVE", conn=test_db)
        
    PipelineStateManager.transition(company_id, "VERIFICATION_PENDING", conn=test_db)
    PipelineStateManager.transition(company_id, "VERIFYING", conn=test_db)
    PipelineStateManager.transition(company_id, "VERIFICATION_FAILED", failure_reason="TEST_REASON", conn=test_db)
    
    # Try recovering a failed verification straight to ACTIVE
    with pytest.raises(TransitionError, match="Illegal transition: VERIFICATION_FAILED -> ACTIVE"):
        PipelineStateManager.transition(company_id, "ACTIVE", conn=test_db)
        
    # Test batch failure on invalid transition
    company_id_2 = "test-invalid-2"
    test_db.execute("INSERT INTO company_identities (company_id, lifecycle_state) VALUES (?, ?)", (company_id_2, "CRAWLING"))
    
    with pytest.raises(TransitionError, match="Illegal transition: CRAWLING -> DISCOVERED"):
        PipelineStateManager.transition_batch([company_id_2], "DISCOVERED", conn=test_db)
