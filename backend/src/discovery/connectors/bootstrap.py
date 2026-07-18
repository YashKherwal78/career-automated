import pkgutil
import importlib
import logging

logger = logging.getLogger("Bootstrap")

def bootstrap_connectors():
    """
    Dynamically discover and import all modules inside src.discovery.connectors.
    This registers them within ConnectorRegistry automatically.
    Returns (discovered_count, imported_count).
    """
    import src.discovery.connectors as connectors
    
    discovered = []
    imported = 0
    
    for _, module_name, _ in pkgutil.iter_modules(connectors.__path__):
        discovered.append(module_name)
        try:
            importlib.import_module(f"{connectors.__name__}.{module_name}")
            imported += 1
        except Exception as e:
            logger.error(f"Failed to bootstrap connector {module_name}: {e}")
            
    logger.info(f"Successfully bootstrapped {imported} connectors out of {len(discovered)} discovered.")
    return len(discovered), imported
