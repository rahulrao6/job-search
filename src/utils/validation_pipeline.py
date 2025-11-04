"""
Comprehensive validation pipeline for search results with detailed confidence scoring.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from src.models.person import Person, PersonCategory
from src.models.job_context import JobContext, CandidateProfile
from src.utils.person_validator import PersonValidator
from src.services.profile_matcher import ProfileMatcher
from src.core.categorizer import PersonCategorizer
from src.utils.ranking_engine import RankingEngine


@dataclass
class ValidationResult:
    """Result of validating a person"""
    person: Person
    is_valid: bool
    confidence_score: float
    validation_details: dict
    match_reasons: List[str]
    quality_score: float
    final_score: float
    rejection_reason: Optional[str] = None


class ValidationPipeline:
    """
    Multi-stage validation pipeline for search results.
    
    Stages:
    1. Basic validation (company match, not spam, etc.)
    2. Confidence scoring (how sure are we this is right person?)
    3. Profile matching (alumni, skills, etc.)
    4. Quality assessment (data completeness, source quality)
    5. Final ranking and filtering
    """
    
    # Minimum thresholds
    MIN_CONFIDENCE = 0.3
    MIN_QUALITY = 0.2
    MIN_FINAL_SCORE = 0.25
    
    def __init__(self):
        self.ranking_engine = RankingEngine()
    
    def process_results(
        self,
        people: List[Person],
        company: str,
        company_domain: Optional[str] = None,
        job_context: Optional[JobContext] = None,
        candidate_profile: Optional[CandidateProfile] = None,
        source_quality_map: Optional[Dict[str, float]] = None
    ) -> Tuple[List[ValidationResult], Dict[str, any]]:
        """
        Process search results through complete validation pipeline.
        
        Returns:
            (validated_results, pipeline_metrics)
        """
        start_time = datetime.now()
        
        # Initialize components
        validator = PersonValidator(company, company_domain)
        profile_matcher = ProfileMatcher()
        categorizer = PersonCategorizer(job_context.title if job_context else "")
        
        # Stage 1: Basic validation and categorization
        stage1_results = []
        rejected_count = 0
        
        for person in people:
            # Categorize first
            person = categorizer.categorize(person)
            
            # Validate
            is_valid, confidence, reason, details = validator.validate_person(person)
            
            if not is_valid and confidence < self.MIN_CONFIDENCE:
                rejected_count += 1
                stage1_results.append(ValidationResult(
                    person=person,
                    is_valid=False,
                    confidence_score=confidence,
                    validation_details=details,
                    match_reasons=[],
                    quality_score=0.0,
                    final_score=0.0,
                    rejection_reason=reason
                ))
            else:
                stage1_results.append(ValidationResult(
                    person=person,
                    is_valid=True,
                    confidence_score=confidence,
                    validation_details=details,
                    match_reasons=[],
                    quality_score=0.0,
                    final_score=0.0
                ))
        
        # Stage 2: Profile matching for valid results
        stage2_results = []
        for result in stage1_results:
            if result.is_valid:
                # Calculate profile match
                relevance_score, match_reasons = profile_matcher.calculate_relevance(
                    result.person,
                    candidate_profile=candidate_profile,
                    job_context=job_context
                )
                
                result.match_reasons = match_reasons
                # Update confidence with relevance
                result.confidence_score = (result.confidence_score + relevance_score) / 2
                
            stage2_results.append(result)
        
        # Stage 3: Quality assessment
        stage3_results = []
        for result in stage2_results:
            if result.is_valid:
                quality_score = self._assess_quality(
                    result.person,
                    result.validation_details,
                    source_quality_map
                )
                result.quality_score = quality_score
                
                # Check minimum quality
                if quality_score < self.MIN_QUALITY:
                    result.is_valid = False
                    result.rejection_reason = "Low quality score"
                    
            stage3_results.append(result)
        
        # Stage 4: Final scoring and ranking
        final_results = []
        for result in stage3_results:
            if result.is_valid:
                # Calculate final score combining all factors
                result.final_score = self._calculate_final_score(
                    confidence=result.confidence_score,
                    quality=result.quality_score,
                    category=result.person.category,
                    match_count=len(result.match_reasons)
                )
                
                # Final threshold check
                if result.final_score < self.MIN_FINAL_SCORE:
                    result.is_valid = False
                    result.rejection_reason = f"Below threshold (score={result.final_score:.2f})"
                    
            final_results.append(result)
        
        # Sort by final score
        final_results.sort(key=lambda r: (r.is_valid, r.final_score), reverse=True)
        
        # Calculate metrics
        processing_time = (datetime.now() - start_time).total_seconds()
        valid_count = sum(1 for r in final_results if r.is_valid)
        
        metrics = {
            'total_processed': len(people),
            'rejected_basic_validation': rejected_count,
            'rejected_quality': sum(1 for r in final_results if not r.is_valid and r.quality_score < self.MIN_QUALITY),
            'rejected_threshold': sum(1 for r in final_results if not r.is_valid and r.final_score < self.MIN_FINAL_SCORE),
            'valid_results': valid_count,
            'processing_time_seconds': processing_time,
            'average_confidence': sum(r.confidence_score for r in final_results if r.is_valid) / max(valid_count, 1),
            'average_quality': sum(r.quality_score for r in final_results if r.is_valid) / max(valid_count, 1),
            'category_breakdown': self._get_category_breakdown(final_results)
        }
        
        return final_results, metrics
    
    def _assess_quality(
        self,
        person: Person,
        validation_details: dict,
        source_quality_map: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Assess overall data quality of a person result.
        
        Considers:
        - Data completeness
        - Source reliability
        - Profile richness
        - Verification signals
        """
        quality_score = 0.5  # Base score
        
        # Data completeness (30%)
        completeness = validation_details['confidence_breakdown'].get('info_completeness', 0.5)
        quality_score += 0.3 * completeness
        
        # Source quality (20%)
        if source_quality_map and person.source:
            source_score = source_quality_map.get(person.source, 0.5)
            quality_score += 0.2 * source_score
        else:
            quality_score += 0.1  # Default source score
            
        # Profile richness (20%)
        richness_score = 0.0
        if person.linkedin_url:
            richness_score += 0.4
        if person.skills and len(person.skills) > 0:
            richness_score += 0.3
        if person.location:
            richness_score += 0.15
        if person.department:
            richness_score += 0.15
        quality_score += 0.2 * richness_score
        
        # Verification signals (30%)
        verification_score = 0.0
        checks_passed = len(validation_details.get('checks_passed', []))
        total_checks = checks_passed + len(validation_details.get('checks_failed', []))
        if total_checks > 0:
            verification_score = checks_passed / total_checks
        quality_score += 0.3 * verification_score
        
        return min(quality_score, 1.0)
    
    def _calculate_final_score(
        self,
        confidence: float,
        quality: float,
        category: PersonCategory,
        match_count: int
    ) -> float:
        """
        Calculate final score combining all factors.
        
        Weights:
        - Confidence: 40%
        - Quality: 30% 
        - Category relevance: 20%
        - Profile matches: 10%
        """
        # Category scores
        category_scores = {
            PersonCategory.RECRUITER: 1.0,
            PersonCategory.MANAGER: 0.9,
            PersonCategory.SENIOR: 0.8,
            PersonCategory.PEER: 0.7,
            PersonCategory.UNKNOWN: 0.3
        }
        
        category_score = category_scores.get(category, 0.5)
        match_score = min(match_count * 0.2, 1.0)  # Each match adds 0.2, capped at 1.0
        
        final_score = (
            0.4 * confidence +
            0.3 * quality +
            0.2 * category_score +
            0.1 * match_score
        )
        
        return final_score
    
    def _get_category_breakdown(self, results: List[ValidationResult]) -> Dict[str, int]:
        """Get count of valid results by category"""
        breakdown = {}
        for result in results:
            if result.is_valid:
                category = result.person.category.value
                breakdown[category] = breakdown.get(category, 0) + 1
        return breakdown
    
    def get_explainable_results(
        self,
        validation_results: List[ValidationResult],
        max_results: int = 10
    ) -> List[Dict[str, any]]:
        """
        Convert validation results to explainable format for UI.
        
        Returns list of dicts with person data and explanations.
        """
        explainable = []
        
        for result in validation_results[:max_results]:
            if not result.is_valid:
                continue
                
            explanation = {
                'person': {
                    'name': result.person.name,
                    'title': result.person.title,
                    'company': result.person.company,
                    'linkedin_url': result.person.linkedin_url,
                    'category': result.person.category.value
                },
                'scores': {
                    'final': round(result.final_score, 2),
                    'confidence': round(result.confidence_score, 2),
                    'quality': round(result.quality_score, 2)
                },
                'match_reasons': result.match_reasons,
                'validation_summary': {
                    'passed': result.validation_details.get('checks_passed', []),
                    'warnings': result.validation_details.get('warnings', [])
                },
                'explanation': self._generate_explanation(result)
            }
            
            explainable.append(explanation)
        
        return explainable
    
    def _generate_explanation(self, result: ValidationResult) -> str:
        """Generate human-readable explanation for why this person was selected"""
        parts = []
        
        # Category explanation
        category_explanations = {
            PersonCategory.RECRUITER: "Recruiter who can help with hiring process",
            PersonCategory.MANAGER: "Manager who might be the hiring manager",
            PersonCategory.SENIOR: "Senior professional in the target role",
            PersonCategory.PEER: "Peer in similar role who could refer",
            PersonCategory.UNKNOWN: "Potential connection at the company"
        }
        parts.append(category_explanations.get(result.person.category, "Connection at company"))
        
        # Match reasons
        if result.match_reasons:
            if 'alumni_match' in str(result.match_reasons):
                parts.append("Alumni connection")
            if 'skills_match' in str(result.match_reasons):
                parts.append("Matching skills")
            if 'department_match' in str(result.match_reasons):
                parts.append("Same department")
                
        # Confidence level
        if result.confidence_score >= 0.8:
            parts.append("High confidence match")
        elif result.confidence_score >= 0.6:
            parts.append("Good match")
            
        return " • ".join(parts)
