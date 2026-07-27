from typing import List, Dict, Any, Optional, Tuple

class EvidenceScorer:
    """
    Evaluates crawls to determine if the payload provides engineering evidence.
    """
    
    @staticmethod
    def evaluate(stats: Dict[str, Any], schema_changed: bool = False, is_low_yield: bool = False) -> Tuple[int, List[str]]:
        """
        Returns a tuple of (score, list_of_reasons).
        Score >= 80 means the evidence should be retained.
        """
        score = 0
        reasons = []
        
        # 1. Schema Change
        if schema_changed:
            score = max(score, 100)
            reasons.append("SCHEMA_CHANGE")
            
        # 2. HTTP Anomalies
        http_status = stats.get("http_status", 0)
        if http_status in (403, 429, 500, 502, 503, 504):
            score = max(score, 95)
            reasons.append(f"HTTP_{http_status}")
            
        # 3. Exceptions
        if not stats.get("success", False):
            exc_type = stats.get("exception_type", "")
            err_msg = str(stats.get("error_message", "")).lower()
            
            if "connector" in exc_type.lower():
                score = max(score, 95)
                reasons.append("CONNECTOR_EXCEPTION")
            elif "parse" in exc_type.lower() or "parse" in err_msg:
                score = max(score, 95)
                reasons.append("PARSER_EXCEPTION")
            elif "timeout" in exc_type.lower() or "timeout" in err_msg:
                score = max(score, 80)
                reasons.append("TIMEOUT")
            else:
                score = max(score, 85)
                reasons.append("UNKNOWN_EXCEPTION")
                
        # 4. Yield Regression
        if is_low_yield:
            score = max(score, 90)
            reasons.append("LOW_YIELD")
            
        # 5. Success Base Score
        if score == 0 and stats.get("success", False):
            score = 5
            reasons.append("SUCCESS")
            
        return score, reasons

    @staticmethod
    def determine_category(reasons: List[str]) -> str:
        """
        Maps reasons to a single terminal category for dashboards.
        """
        priority_categories = [
            "SCHEMA_CHANGE",
            "HTTP_403", "HTTP_429", "HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504",
            "PARSER_EXCEPTION", "CONNECTOR_EXCEPTION", "TIMEOUT", "LOW_YIELD"
        ]
        
        for p in priority_categories:
            if p in reasons:
                # Group HTTP anomalies
                if p.startswith("HTTP_"):
                    return p
                return p
                
        if "UNKNOWN_EXCEPTION" in reasons:
            return "UNKNOWN"
            
        if "SUCCESS" in reasons:
            return "SUCCESS"
            
        return "UNKNOWN"
