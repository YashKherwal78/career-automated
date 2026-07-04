import yaml
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseExecutor(ABC):
    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

class NativeExecutor(BaseExecutor):
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        print("[Executor] Running natively inside Antigravity...")
        return {"status": "executed", "executor": "native"}

class AiderExecutor(BaseExecutor):
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        print("[Executor] Spawning Aider for large-scale refactor...")
        return {"status": "executed", "executor": "aider"}

class ExecutorRegistry:
    """
    Policy-driven Executor Registry.
    Routes execution to Native or Aider based on routing.yaml.
    """
    def __init__(self, routing_path: str = ".antigravity/routing.yaml"):
        with open(routing_path, "r") as f:
            self.policy = yaml.safe_load(f).get("routing", {})
            
        self.executors = {
            "native": NativeExecutor(),
            "aider": AiderExecutor()
        }

    def route(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Default to native if unknown
        policy_config = self.policy.get(task_type, {"executor": "native"})
        executor_name = policy_config.get("executor", "native")
        
        executor = self.executors.get(executor_name)
        if not executor:
            raise ValueError(f"Unknown executor defined in policy: {executor_name}")
            
        print(f"[Registry] Task Type '{task_type}' mapped to executor: {executor_name}")
        return executor.execute(payload)
