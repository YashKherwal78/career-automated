from src.system.logger import setup_logger
logger = setup_logger('integration_registry')
import os
import sys

from enum import Enum

class IntegrationStatus(Enum):
    READY = "READY"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

def get_registry() -> dict:
    """
    Centralized source of truth for all third-party integrations and internal handlers.
    This ensures Dashboard, Health Check, and Pipeline Orchestrator all share the same state.
    """
    
    registry = {
        "Groq": IntegrationStatus.READY,
        "SMTP": IntegrationStatus.READY,
        "IMAP": IntegrationStatus.READY,
        "Playwright": IntegrationStatus.READY,
        
        # Application Handlers
        "Greenhouse": IntegrationStatus.READY,
        "Wellfound": IntegrationStatus.NOT_IMPLEMENTED,
        "Lever": IntegrationStatus.NOT_IMPLEMENTED,
        "Ashby": IntegrationStatus.NOT_IMPLEMENTED,
        
        # Scrapers & Data Sources
        "LinkedIn": IntegrationStatus.READY,
        "Apify": IntegrationStatus.READY,
        
        # Outreach
        "EmailOutreach": IntegrationStatus.NOT_IMPLEMENTED
    }
    
    return registry

def print_registry():
    registry = get_registry()
    logger.info("\n--- Integration Registry ---")
    for name, status in registry.items():
        logger.info(f"{name.ljust(25)} {status.value}")
    logger.info("----------------------------\n")
    
if __name__ == "__main__":
    print_registry()
