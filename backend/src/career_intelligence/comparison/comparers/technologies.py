from typing import List, Dict, Any
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, TechnologyComparison
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.ontology.interfaces import GraphService
from src.career_intelligence.ontology.backend import MemoryGraphBackend
from src.career_intelligence.ontology.service import CareerGraphService
from src.career_intelligence.ontology.cache import CachedGraphService
from src.career_intelligence.ontology.loader import OntologyLoader

class TechnologyComparer(ComparerInterface):
    def __init__(self, ontology: GraphService = None):
        if ontology is None:
            backend = MemoryGraphBackend()
            loader = OntologyLoader(backend)
            loader.load_default_fixtures()
            raw_service = CareerGraphService(backend)
            self.ontology = CachedGraphService(raw_service)
        else:
            self.ontology = ontology

    def compare(self, profile: CandidateProfile, job: StructuredJob) -> TechnologyComparison:
        """Compares technologies required by job description vs candidate profile technologies using Career Ontology."""
        job_techs = {t.lower() for t in job.technologies}
        if not job_techs:
            return TechnologyComparison(score=1.0, reasoning=["No technology requirements specified by the job description."])

        candidate_techs = set()
        for cat in ["programming_languages", "frameworks", "libraries", "databases", "cloud", "ai_ml", "developer_tools"]:
            for t in getattr(profile.skills, cat, []):
                candidate_techs.add(t.lower())

        for exp in profile.experience:
            for t in exp.technologies:
                candidate_techs.add(t.lower())
        for proj in profile.projects:
            for t in proj.technologies:
                candidate_techs.add(t.lower())

        exact_matches = []
        semantic_matches = []
        alias_matches = []
        related_matches = []
        missing = []
        reasoning = []

        for req in job.technologies:
            req_lower = req.lower()
            if req_lower in candidate_techs:
                exact_matches.append(req)
                reasoning.append(f"Matched {req} exactly.")
            else:
                # Check CareerOntology for semantic similarity mappings
                matched_semantically = False
                for cand_tech in candidate_techs:
                    sim = self.ontology.check_similarity(cand_tech, req_lower)
                    if sim >= 0.8:
                        semantic_matches.append(req)
                        reasoning.append(f"Matched {req} semantically via {cand_tech.title()} (Similarity: {int(sim*100)}%).")
                        matched_semantically = True
                        break
                    elif sim >= 0.5:
                        related_matches.append(req)
                        reasoning.append(f"Identified relation between {req} and candidate {cand_tech.title()} (Similarity: {int(sim*100)}%).")
                        matched_semantically = True
                        break
                
                if not matched_semantically:
                    missing.append(req)

        # Match calculation: exact counts + half credit for related/semantic matches
        matched_count = len(exact_matches) + (len(semantic_matches) * 0.8) + (len(related_matches) * 0.5)
        score = min(1.0, matched_count / len(job_techs))

        # Recommended learning order (technologies they don't have, starting with prerequisites)
        recommended_learning = []
        for m in missing:
            prereqs = self.ontology.get_prerequisites(m)
            if prereqs:
                for p in prereqs:
                    if p.title() not in recommended_learning:
                        recommended_learning.append(p.title())
            if m.title() not in recommended_learning:
                recommended_learning.append(m.title())

        return TechnologyComparison(
            score=score,
            matched=exact_matches + semantic_matches,
            missing=missing,
            exact_matches=exact_matches,
            semantic_matches=semantic_matches,
            alias_matches=alias_matches,
            related_matches=related_matches,
            recommended_learning_order=recommended_learning,
            reasoning=reasoning,
            confidence=0.95
        )
