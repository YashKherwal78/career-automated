import os
import yaml
from typing import Dict, Any, List
from dataclasses import dataclass
from src.discovery.search_planner import SearchTask

@dataclass
class MatchResult:
    relevance_score: int
    opportunity_score: int
    confidence: float
    final_score: int
    recommendation: str
    explanation: List[str]

class MatchEngine:
    """
    Evaluates opportunities and returns a transparent dual-score with a recommendation.
    Driven by matching_weights.yaml.
    """
    
    def __init__(self, config_path: str = None, taxonomy_path: str = None):
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), "matching_weights.yaml")
        if not taxonomy_path:
            taxonomy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "role_taxonomy.yaml")
        
        with open(config_path, 'r') as f:
            self.weights = yaml.safe_load(f)
            
        try:
            with open(taxonomy_path, 'r') as f:
                self.taxonomy = yaml.safe_load(f)
        except Exception:
            self.taxonomy = {}

    def _determine_recommendation(self, final_score: int) -> str:
        t = self.weights.get("recommendation_thresholds", {})
        if final_score >= t.get("apply_now", 85):
            return "APPLY_NOW"
        elif final_score >= t.get("apply_if_time", 65):
            return "APPLY_IF_TIME"
        elif final_score >= t.get("save_for_later", 40):
            return "SAVE_FOR_LATER"
        return "IGNORE"
        
    def _compute_confidence(self, job: Dict[str, Any], source: str) -> float:
        # Example dynamic signal confidence
        if source == "PipelineA_ATS":
            return 0.95
        if job.get("description"):
            return 0.85
        return 0.50  # Just title and metadata

    def score_job(self, job: Dict[str, Any], task: SearchTask, source: str) -> MatchResult:
        rel_weights = self.weights.get("relevance", {})
        opp_weights = self.weights.get("opportunity", {})
        soft_rejects = self.weights.get("soft_rejects", {})
        
        relevance_score = 0
        opportunity_score = 0
        explanations = []
        
        title = job.get("title", job.get("positionName", "")).strip()
        title_lower = title.lower()
        location = job.get("location", job.get("jobLocation", "")).lower()
        
        # --- RELEVANCE SCORING (JIE DRIVEN) ---
        fit = job.get("candidate_fit")
        if fit:
            # 1. Experience Score
            exp_fit = fit.get("experience", {})
            if exp_fit.get("fit", False):
                val = rel_weights.get("experience_fit", 25)
                relevance_score += val
                explanations.append(f"[Relevance] +{val} {exp_fit.get('reason', '')}")
            else:
                pen = -25 # Hard penalty
                relevance_score += pen
                explanations.append(f"[Relevance] {pen} {exp_fit.get('reason', '')}")

            # 2. Skill Coverage Score
            skills_gap = fit.get("skills", {})
            coverage = skills_gap.get("coverage", 0.0)
            missing = skills_gap.get("missing", [])
            
            if coverage > 0:
                # Up to 35 points for 100% skill match
                val = int(coverage * 35)
                relevance_score += val
                explanations.append(f"[Relevance] +{val} Skill coverage ({coverage * 100:.0f}%)")
                if missing:
                    explanations.append(f"[Relevance] Missing key skills: {', '.join(missing)}")
            
            # 3. Location/Work Mode
            jie_mode = job.get("jie", {}).get("work_mode", "Unknown")
            if "Remote" in task.work_modes and (jie_mode == "Remote" or "remote" in title_lower or "remote" in location):
                val = rel_weights.get("remote", 10)
                relevance_score += val
                explanations.append(f"[Relevance] +{val} Remote work match")
            elif "Hybrid" in task.work_modes and jie_mode == "Onsite":
                pen = soft_rejects.get("onsite_penalty", -10)
                relevance_score += pen
                explanations.append(f"[Relevance] {pen} Onsite instead of Hybrid (Soft Reject)")
                
        else:
            # Fallback to title-based heuristics if no JIE data (e.g. old data)
            role_family = task.role_family
            taxonomy_for_role = self.taxonomy.get(role_family, {})
            role_weights = rel_weights.get("role_fit", {})
            
            assigned_tier = None
            for tier in ["reject", "weak", "adjacent", "exact", "core"]:
                keywords = taxonomy_for_role.get(tier, [])
                for kw in keywords:
                    if kw.lower() in title_lower:
                        assigned_tier = tier
                        break
                if assigned_tier:
                    break
                    
            if not assigned_tier:
                core_keywords = [w.lower() for w in task.canonical_query.split()]
                matched_words = [w for w in core_keywords if w in title_lower]
                if len(matched_words) == len(core_keywords):
                    assigned_tier = "core"
                elif len(matched_words) > 0:
                    assigned_tier = "adjacent"
                else:
                    assigned_tier = "weak"
                    
            val = role_weights.get(assigned_tier, 0)
            relevance_score += val
            explanations.append(f"[Relevance] {val:+d} Role match tier: {assigned_tier} (Fallback)")


        # --- OPPORTUNITY SCORING (Dynamic Signals) ---
        # 1. Official ATS
        if source == "PipelineA_ATS":
            val = opp_weights.get("official_ats", 5)
            opportunity_score += val
            explanations.append(f"[Opportunity] +{val} Official ATS source")
            
        # 2. Freshness
        val = opp_weights.get("freshness", 15)
        opportunity_score += val
        explanations.append(f"[Opportunity] +{val} Freshly posted (inferred)")
        
        # 3. Company Priority (Simulated dynamic signal)
        # E.g. Check if job has multiple occurrences or is in registry
        val = opp_weights.get("company_priority", 20)
        opportunity_score += val
        explanations.append(f"[Opportunity] +{val} Recognized startup priority")

        
        confidence = self._compute_confidence(job, source)
        
        conf_adj_config = self.weights.get("confidence_adjustment", {})
        max_bonus = conf_adj_config.get("max_bonus", 10)
        min_penalty = conf_adj_config.get("min_penalty", -10)
        
        # Linear scale: 1.0 confidence -> max_bonus, 0.0 confidence -> min_penalty
        conf_adjustment = int(min_penalty + (max_bonus - min_penalty) * confidence)
        
        final_score = int(relevance_score + opportunity_score + conf_adjustment)
        if conf_adjustment >= 0:
            explanations.append(f"[Confidence] +{conf_adjustment} Additive Adjustment ({confidence:.2f} conf)")
        else:
            explanations.append(f"[Confidence] {conf_adjustment} Additive Adjustment ({confidence:.2f} conf)")
            
        recommendation = self._determine_recommendation(final_score)

        return MatchResult(
            relevance_score=relevance_score,
            opportunity_score=opportunity_score,
            confidence=confidence,
            final_score=final_score,
            recommendation=recommendation,
            explanation=explanations
        )
