import sys
import time
import uuid
from src.runtime.postgres.connection import get_connection
from src.runtime.redis.redis_client import RedisClient
from src.runtime.redis.queue_manager import QueueManager
from src.runtime.redis.lock_manager import LockManager
from src.runtime.redis.heartbeat_manager import HeartbeatManager
from src.runtime.storage.storage_service import StorageService

def run_smoke_test():
    print("=== STARTING RUNTIME SMOKE TEST ===")
    
    # 1. PostgreSQL Read/Write Test
    print("\n1. Testing PostgreSQL Read/Write...")
    try:
        with get_connection() as conn:
            # We insert a heartbeat check on worker_states or raw query
            cursor = conn.execute("SELECT 1")
            row = cursor.fetchone()
            # Handle both dictionary rows and tuple rows
            val = list(row.values())[0] if isinstance(row, dict) or hasattr(row, "values") else row[0]
            if val != 1:
                raise ValueError("Expected select 1 to return 1")
            print(" -> PostgreSQL: PASS")
    except Exception as e:
        print(f" -> PostgreSQL: FAIL ({e})")
        sys.exit(1)

    # 2. Redis Queue Enqueue/Dequeue Test
    print("\n2. Testing Redis Queue...")
    try:
        test_queue = "smoke_test_queue"
        payload = {"test_uuid": str(uuid.uuid4())}
        QueueManager.enqueue(test_queue, payload)
        dequeued = QueueManager.dequeue(test_queue, timeout=2)
        if not dequeued or dequeued.get("test_uuid") != payload["test_uuid"]:
            raise ValueError(f"Payload mismatch: expected {payload}, got {dequeued}")
        print(" -> Redis Queue: PASS")
    except Exception as e:
        print(f" -> Redis Queue: FAIL ({e})")
        sys.exit(1)

    # 3. Redis Lock Acquisition/Release Test
    print("\n3. Testing Redis Lock...")
    try:
        lock_name = "smoke_test_lock"
        acquired = LockManager.acquire_lock(lock_name, acquire_timeout=1, lock_timeout=10)
        if not acquired:
            raise ValueError("Failed to acquire lock")
        # Try to acquire lock again (should fail)
        second_acquired = LockManager.acquire_lock(lock_name, acquire_timeout=1, lock_timeout=5)
        if second_acquired:
            raise ValueError("Acquired lock twice (violates mutual exclusion!)")
        # Release lock
        LockManager.release_lock(lock_name)
        # Try to acquire lock again (should pass)
        third_acquired = LockManager.acquire_lock(lock_name, acquire_timeout=1, lock_timeout=5)
        if not third_acquired:
            raise ValueError("Failed to acquire lock after release")
        LockManager.release_lock(lock_name)
        print(" -> Redis Lock: PASS")
    except Exception as e:
        print(f" -> Redis Lock: FAIL ({e})")
        sys.exit(1)

    # 4. Redis Heartbeat Tracking Test
    print("\n4. Testing Redis Heartbeat...")
    try:
        worker_id = f"smoke-worker-{uuid.uuid4().hex[:6]}"
        HeartbeatManager.register_worker(worker_id, {"env": "smoke-test"})
        active = HeartbeatManager.get_active_workers()
        active_ids = [w["worker_id"] for w in active]
        if worker_id not in active_ids:
            raise ValueError(f"Worker {worker_id} not found in active list: {active_ids}")
        print(" -> Redis Heartbeat: PASS")
    except Exception as e:
        print(f" -> Redis Heartbeat: FAIL ({e})")
        sys.exit(1)

    # 5. Cloudflare R2 Upload/Download/Delete Test
    print("\n5. Testing Cloudflare R2 Storage...")
    try:
        test_file = "smoke_upload_test.txt"
        test_key = "snapshots/smoke_test.txt"
        with open(test_file, "w") as f:
            f.write("Smoke test R2 content")
            
        uploaded = StorageService.upload_file(test_file, test_key)
        if not uploaded:
            raise ValueError("Upload failed")
            
        download_dest = "smoke_download_dest.txt"
        downloaded = StorageService.download_file(test_key, download_dest)
        if not downloaded:
            raise ValueError("Download failed")
            
        with open(download_dest, "r") as f:
            content = f.read()
            if content != "Smoke test R2 content":
                raise ValueError(f"Content mismatch: expected 'Smoke test R2 content', got '{content}'")
                
        deleted = StorageService.delete_file(test_key)
        if not deleted:
            raise ValueError("Delete failed")
            
        import os
        os.remove(test_file)
        os.remove(download_dest)
        print(" -> Cloudflare R2: PASS")
    except Exception as e:
        print(f" -> Cloudflare R2: FAIL ({e})")
        sys.exit(1)

    print("\n======================================")
    print("🎉 ALL INFRASTRUCTURE SMOKE TESTS PASSED!")
    print("======================================")

if __name__ == "__main__":
    run_smoke_test()
