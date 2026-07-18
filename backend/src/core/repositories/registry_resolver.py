class RegistryResolver:
    """
    Centralizes the logic for determining the table names for provider-specific registries.
    This guarantees that if registry table naming conventions change, it only happens here.
    """
    
    @staticmethod
    def _sanitize(provider: str) -> str:
        return "".join([c if c.isalnum() else '_' for c in provider])

    @staticmethod
    def metadata_table(provider: str) -> str:
        return "ats_registry"

    @staticmethod
    def state_table(provider: str) -> str:
        return "ats_registry"

    @staticmethod
    def history_table(provider: str) -> str:
        return "registry_history"
