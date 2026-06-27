from typing import List, Dict, Any

class BaseDiscoverySource:
    """
    Interface for all Opportunity Discovery Sources.
    Sources are strictly responsible for returning a List of Opportunity dictionaries.
    They must have zero awareness of databases, filtering, or downstream systems.
    """
    def discover_opportunities(self, *args, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError("Subclasses must implement discover_opportunities")
