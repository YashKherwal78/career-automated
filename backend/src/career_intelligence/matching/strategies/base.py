from typing import Dict

class WeightStrategy:
    def get_weights(self) -> Dict[str, float]:
        """Returns category weighting configurations for this strategy."""
        raise NotImplementedError("Subclasses must implement get_weights()")
