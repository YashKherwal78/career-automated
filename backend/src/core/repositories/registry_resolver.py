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
        safe_provider = RegistryResolver._sanitize(provider)
        return f"registry_{safe_provider}"

    @staticmethod
    def state_table(provider: str) -> str:
        safe_provider = RegistryResolver._sanitize(provider)
        return f"registry_{safe_provider}_state"

    @staticmethod
    def history_table(provider: str) -> str:
        safe_provider = RegistryResolver._sanitize(provider)
        return f"registry_{safe_provider}_history"
