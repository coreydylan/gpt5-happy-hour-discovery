"""
GPT-5 Happy Hour Discovery System - Mathematical Consensus Engine
The core differentiator: transforms agent claims into confidence-scored truth

This module implements the deterministic truth-finding algorithm that:
1. Weighs evidence by source reliability, recency, and specificity
2. Detects and penalizes contradictions
3. Produces field-level confidence scores  
4. Flags ambiguous data for human review

Mathematical Foundation:
support(v) = Σᵢ [w_source(i) × w_time(i) × s_specificity(i) × s_agent(i)]
score(v) = σ(support(v) - contradiction_penalty(v))
"""

import math
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Tuple, Optional, Set
from uuid import UUID

from .models import (
    AgentClaim, 
    ConsensusResult, 
    FieldConfidence, 
    HappyHourSchedule,
    SourceType, 
    Specificity, 
    Modality,
    AgentType
)


# ============================================================================
# CONSENSUS CONFIGURATION
# ============================================================================

class ConsensusConfig:
    """Configuration for consensus algorithm weights and thresholds"""
    
    # Source reliability weights (Tier A → Tier E from comprehensive plan)
    SOURCE_WEIGHTS: Dict[SourceType, float] = {
        # Tier A - Owner/Official (Weight: 1.0)
        SourceType.WEBSITE: 1.0,
        SourceType.PHONE_CALL: 1.0,
        SourceType.EMAIL: 1.0,
        
        # Tier B - High-Coverage User Generated (Weight: 0.5-0.85)
        SourceType.GOOGLE_POST: 0.85,      # Owner-managed posts
        SourceType.GOOGLE_QA: 0.75,        # Q&A often has owner responses
        SourceType.RESY_EVENT: 0.75,       # Owner-managed events
        SourceType.OPENTABLE_EVENT: 0.75,  # Owner-managed events
        SourceType.UNTAPPD_MENU: 0.7,      # Live menu data
        SourceType.BEERMENU: 0.7,          # Live menu data
        SourceType.GOOGLE_REVIEW: 0.5,     # User-generated
        SourceType.YELP_REVIEW: 0.5,       # User-generated
        SourceType.YELP_PHOTO: 0.45,       # Photos can be outdated
        SourceType.FACEBOOK_POST: 0.6,     # Mix of owner/user content
        SourceType.INSTAGRAM_POST: 0.55,   # Mix of owner/user content
        SourceType.INSTAGRAM_COMMENT: 0.4, # Comments are volatile
        SourceType.MENU_PDF: 0.8,          # Official but may be outdated
    }
    
    # Specificity bonuses (multiply base weight)
    SPECIFICITY_MULTIPLIERS: Dict[Specificity, float] = {
        Specificity.EXACT: 1.2,        # "3:00pm - 6:00pm"
        Specificity.APPROXIMATE: 1.0,   # "around 3-6pm"  
        Specificity.VAGUE: 0.8,         # "afternoon"
        Specificity.IMPLIED: 0.6,       # "after work specials"
    }
    
    # Modality bonuses (multiply base weight)
    MODALITY_MULTIPLIERS: Dict[Modality, float] = {
        Modality.STRUCTURED_DATA: 1.15,  # API responses
        Modality.VOICE: 1.1,             # Phone call transcripts
        Modality.TEXT: 1.0,              # Text extraction
        Modality.IMAGE_OCR: 0.9,         # OCR can have errors
    }
    
    # Recency decay half-lives (in days)
    HALF_LIFE_DAYS: Dict[str, int] = {
        'default': 30,          # Standard venues: 30-day half-life
        'sports_bar': 7,        # Sports bars change for game days
        'tourist': 3,           # Vegas/tourist areas change frequently
        'seasonal': 14,         # Seasonal venues
        'chain': 60,            # Chain restaurants more stable
    }
    
    # Confidence thresholds
    CONFIDENCE_THRESHOLDS = {
        'confirmed': 0.85,      # Publish as "confirmed"
        'provisional': 0.65,    # Mark "provisional", schedule VoiceVerify
        'needs_review': 0.65,   # Below this = human review
    }
    
    # Contradiction detection
    CONTRADICTION_PENALTY = 0.15        # Penalty for conflicting claims
    MIN_CONFIDENCE_GAP = 0.10          # Min gap between top-1 and top-2 for clarity
    
    # Human review triggers
    REVIEW_TRIGGERS = {
        'min_sources': 2,               # Need at least 2 sources
        'min_completeness': 0.6,        # 60% of fields filled
        'max_contradiction_rate': 0.3,  # 30% of claims conflict
        'min_confidence': 0.65,         # Overall confidence threshold
    }


# ============================================================================
# CORE CONSENSUS ENGINE
# ============================================================================

class ConsensusEngine:
    """
    Mathematical consensus engine that transforms agent claims into 
    confidence-scored truth using deterministic algorithms
    """
    
    def __init__(self, config: Optional[ConsensusConfig] = None):
        self.config = config or ConsensusConfig()
    
    def compute_consensus(
        self, 
        claims: List[AgentClaim], 
        venue_type: str = 'default'
    ) -> ConsensusResult:
        """
        Main consensus computation: transform agent claims into final result
        
        Args:
            claims: List of agent claims to process
            venue_type: Type of venue for recency weighting
            
        Returns:
            ConsensusResult with confidence scores and final data
        """
        
        if not claims:
            raise ValueError("Cannot compute consensus with no claims")
        
        # Group claims by field path
        field_claims = self._group_claims_by_field(claims)
        
        # Compute consensus for each field
        field_confidences = []
        consensus_data = {}
        
        for field_path, field_claims_list in field_claims.items():
            field_result = self._compute_field_consensus(
                field_path, field_claims_list, venue_type
            )
            
            if field_result:
                field_confidences.append(field_result)
                consensus_data[field_path] = field_result.field_value
        
        # Build final happy hour schedule from consensus data
        happy_hour_schedule = self._build_happy_hour_schedule(consensus_data)
        
        # Calculate overall metrics
        overall_confidence = self._calculate_overall_confidence(field_confidences)
        completeness_score = self._calculate_completeness_score(consensus_data)
        
        # Determine if human review is needed
        needs_review, review_reasons = self._assess_review_needs(
            field_confidences, claims, overall_confidence, completeness_score
        )
        
        return ConsensusResult(
            cri_id=claims[0].claim_id,  # Placeholder - should come from job context
            restaurant_name=self._extract_restaurant_name(claims),
            happy_hour_data=happy_hour_schedule,
            overall_confidence=overall_confidence,
            field_confidences=field_confidences,
            completeness_score=completeness_score,
            evidence_count=len(claims),
            source_diversity=len(set(claim.source_type for claim in claims)),
            needs_human_review=needs_review,
            review_reasons=review_reasons,
            agent_results_used=[claim.claim_id for claim in claims]
        )
    
    def _group_claims_by_field(self, claims: List[AgentClaim]) -> Dict[str, List[AgentClaim]]:
        """Group claims by field path for field-level consensus"""
        field_claims = defaultdict(list)
        
        for claim in claims:
            field_claims[claim.field_path].append(claim)
        
        return dict(field_claims)
    
    def _compute_field_consensus(
        self, 
        field_path: str, 
        claims: List[AgentClaim], 
        venue_type: str
    ) -> Optional[FieldConfidence]:
        """
        Compute consensus for a single field using mathematical truth-finding
        
        This implements the core algorithm:
        support(v) = Σᵢ [w_source(i) × w_time(i) × s_specificity(i) × s_agent(i)]
        """
        
        if not claims:
            return None
        
        # Group claims by candidate value
        value_claims = defaultdict(list)
        for claim in claims:
            # Normalize value for comparison (convert to string for grouping)
            value_key = self._normalize_value_for_comparison(claim.field_value)
            value_claims[value_key].append(claim)
        
        # Calculate support score for each candidate value
        value_scores = {}
        
        for value_key, value_claims_list in value_claims.items():
            total_support = Decimal('0.0')
            source_weight_sum = Decimal('0.0')
            recency_weight_sum = Decimal('0.0')
            specificity_bonus = Decimal('0.0')
            
            for claim in value_claims_list:
                # Component weights
                w_source = Decimal(str(self._get_source_weight(claim.source_type)))
                w_time = Decimal(str(self._get_recency_weight(claim.observed_at, venue_type)))
                w_specificity = Decimal(str(self._get_specificity_weight(claim.specificity)))
                w_modality = Decimal(str(self._get_modality_weight(claim.modality)))
                w_agent = Decimal(str(claim.agent_confidence))
                
                # Calculate support for this claim
                claim_support = w_source * w_time * w_specificity * w_modality * w_agent
                total_support += claim_support
                
                # Track components for debugging
                source_weight_sum += w_source
                recency_weight_sum += w_time  
                specificity_bonus += w_specificity
            
            # Apply contradiction penalty
            contradiction_penalty = self._calculate_contradiction_penalty(
                value_key, value_claims, venue_type
            )
            
            final_score = total_support - Decimal(str(contradiction_penalty))
            
            value_scores[value_key] = {
                'score': float(final_score),
                'claims': value_claims_list,
                'source_weight_sum': source_weight_sum,
                'recency_weight_sum': recency_weight_sum, 
                'specificity_bonus': specificity_bonus,
                'contradiction_penalty': Decimal(str(contradiction_penalty))
            }
        
        # Find winner (highest score)
        if not value_scores:
            return None
        
        winner_key = max(value_scores.keys(), key=lambda k: value_scores[k]['score'])
        winner_data = value_scores[winner_key]
        
        # Calculate confidence using sigmoid function for normalization
        confidence = self._sigmoid(winner_data['score'])
        
        # Check if result is ambiguous (small gap between top candidates)
        sorted_scores = sorted(value_scores.values(), key=lambda x: x['score'], reverse=True)
        is_ambiguous = False
        
        if len(sorted_scores) > 1:
            score_gap = sorted_scores[0]['score'] - sorted_scores[1]['score']
            if score_gap < self.config.MIN_CONFIDENCE_GAP:
                is_ambiguous = True
        
        # Build field confidence result
        supporting_claims = [claim.claim_id for claim in winner_data['claims']]
        conflicting_claims = []
        
        # Find conflicting claims (claims for other values)
        for value_key, data in value_scores.items():
            if value_key != winner_key:
                conflicting_claims.extend([claim.claim_id for claim in data['claims']])
        
        return FieldConfidence(
            field_path=field_path,
            field_value=winner_data['claims'][0].field_value,  # Use actual value from winning claim
            confidence=confidence,
            supporting_claims=supporting_claims,
            conflicting_claims=conflicting_claims,
            source_weight_sum=winner_data['source_weight_sum'],
            recency_weight_sum=winner_data['recency_weight_sum'],
            specificity_bonus=winner_data['specificity_bonus'],
            contradiction_penalty=winner_data['contradiction_penalty']
        )
    
    def _get_source_weight(self, source_type: SourceType) -> float:
        """Get reliability weight for source type"""
        return self.config.SOURCE_WEIGHTS.get(source_type, 0.3)  # Default to editorial weight
    
    def _get_recency_weight(self, observed_at: datetime, venue_type: str) -> float:
        """
        Calculate recency weight using exponential decay
        w_time = exp(-age_days / half_life)
        """
        now = datetime.utcnow()
        age_days = (now - observed_at).days
        half_life = self.config.HALF_LIFE_DAYS.get(venue_type, 30)
        
        return math.exp(-age_days / half_life)
    
    def _get_specificity_weight(self, specificity: Specificity) -> float:
        """Get bonus multiplier for specificity level"""
        return self.config.SPECIFICITY_MULTIPLIERS.get(specificity, 1.0)
    
    def _get_modality_weight(self, modality: Modality) -> float:
        """Get bonus multiplier for extraction modality"""
        return self.config.MODALITY_MULTIPLIERS.get(modality, 1.0)
    
    def _calculate_contradiction_penalty(
        self, 
        value_key: str, 
        all_value_claims: Dict[str, List[AgentClaim]], 
        venue_type: str
    ) -> float:
        """
        Calculate penalty for contradicting claims
        Higher penalty when high-quality sources disagree
        """
        
        # Find claims that contradict this value
        contradicting_claims = []
        for other_value_key, other_claims in all_value_claims.items():
            if other_value_key != value_key:
                contradicting_claims.extend(other_claims)
        
        if not contradicting_claims:
            return 0.0
        
        # Calculate penalty based on quality of contradicting evidence
        penalty = 0.0
        for claim in contradicting_claims:
            source_weight = self._get_source_weight(claim.source_type)
            recency_weight = self._get_recency_weight(claim.observed_at, venue_type)
            
            # Higher penalty for contradictions from high-quality, recent sources
            claim_penalty = source_weight * recency_weight * self.config.CONTRADICTION_PENALTY
            penalty += claim_penalty
        
        return penalty
    
    def _normalize_value_for_comparison(self, value: Any) -> str:
        """Normalize values for comparison (handle slight variations)"""
        if isinstance(value, str):
            # Normalize time strings, remove extra spaces, etc.
            normalized = value.lower().strip()
            normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single
            return normalized
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, dict):
            # For time slots, etc. - convert to comparable string
            return str(sorted(value.items())) if value else ""
        elif isinstance(value, list):
            return str(sorted(value)) if value else ""
        else:
            return str(value)
    
    def _sigmoid(self, x: float) -> float:
        """
        Apply sigmoid function for confidence normalization
        Maps arbitrary support scores to [0, 1] range
        """
        return 1.0 / (1.0 + math.exp(-x))
    
    def _build_happy_hour_schedule(self, consensus_data: Dict[str, Any]) -> HappyHourSchedule:
        """Build structured happy hour schedule from consensus field data"""
        # This would parse the consensus field data and build a proper HappyHourSchedule
        # For now, return a basic structure - full implementation would map field paths
        # like "schedule.monday[0].start" back to the nested structure
        
        return HappyHourSchedule(
            status="unknown",  # Would be determined from consensus data
            weekly_schedule=[],  # Would be built from schedule.* fields
            drink_offers=[],     # Would be built from offers.drinks.* fields
            food_offers=[]       # Would be built from offers.food.* fields
        )
    
    def _calculate_overall_confidence(self, field_confidences: List[FieldConfidence]) -> float:
        """Calculate overall confidence as weighted average of field confidences"""
        if not field_confidences:
            return 0.0
        
        # Weight important fields higher (schedule, status more important than fine print)
        field_weights = {
            'status': 3.0,
            'schedule': 2.5, 
            'offers': 2.0,
            'areas': 1.5,
            'fine_print': 1.0
        }
        
        total_weighted_confidence = 0.0
        total_weights = 0.0
        
        for field_conf in field_confidences:
            # Determine weight based on field path
            weight = 1.0
            for field_prefix, field_weight in field_weights.items():
                if field_conf.field_path.startswith(field_prefix):
                    weight = field_weight
                    break
            
            total_weighted_confidence += field_conf.confidence * weight
            total_weights += weight
        
        return total_weighted_confidence / total_weights if total_weights > 0 else 0.0
    
    def _calculate_completeness_score(self, consensus_data: Dict[str, Any]) -> float:
        """Calculate how complete the extracted data is (0.0 - 1.0)"""
        
        # Define expected fields for a complete happy hour record
        expected_fields = {
            'status',
            'schedule.weekly',
            'offers.drinks', 
            'offers.food',
            'areas_applicable',
            'dine_in_only'
        }
        
        # Count how many expected fields we have data for
        found_fields = set()
        
        for field_path in consensus_data.keys():
            # Check if this field path matches any expected field
            for expected in expected_fields:
                if field_path.startswith(expected):
                    found_fields.add(expected)
        
        return len(found_fields) / len(expected_fields)
    
    def _assess_review_needs(
        self, 
        field_confidences: List[FieldConfidence],
        claims: List[AgentClaim],
        overall_confidence: float, 
        completeness_score: float
    ) -> Tuple[bool, List[str]]:
        """Determine if human review is needed and why"""
        
        needs_review = False
        reasons = []
        
        # Check confidence threshold
        if overall_confidence < self.config.REVIEW_TRIGGERS['min_confidence']:
            needs_review = True
            reasons.append(f"Low overall confidence: {overall_confidence:.2f}")
        
        # Check completeness
        if completeness_score < self.config.REVIEW_TRIGGERS['min_completeness']:
            needs_review = True  
            reasons.append(f"Incomplete data: {completeness_score:.2f} completeness")
        
        # Check source diversity
        source_types = set(claim.source_type for claim in claims)
        if len(source_types) < self.config.REVIEW_TRIGGERS['min_sources']:
            needs_review = True
            reasons.append(f"Insufficient sources: {len(source_types)} unique source types")
        
        # Check contradiction rate
        total_fields = len(field_confidences)
        conflicted_fields = sum(1 for fc in field_confidences if fc.conflicting_claims)
        
        if total_fields > 0:
            contradiction_rate = conflicted_fields / total_fields
            if contradiction_rate > self.config.REVIEW_TRIGGERS['max_contradiction_rate']:
                needs_review = True
                reasons.append(f"High contradiction rate: {contradiction_rate:.2f}")
        
        # Check for ambiguous results (low confidence gaps)
        ambiguous_fields = []
        for fc in field_confidences:
            if fc.confidence < 0.8 and fc.conflicting_claims:
                ambiguous_fields.append(fc.field_path)
        
        if ambiguous_fields:
            needs_review = True
            reasons.append(f"Ambiguous fields: {', '.join(ambiguous_fields[:3])}")
        
        return needs_review, reasons
    
    def _extract_restaurant_name(self, claims: List[AgentClaim]) -> str:
        """Extract restaurant name from claims"""
        # Look for name field in claims
        for claim in claims:
            if claim.field_path == 'name' and isinstance(claim.field_value, str):
                return claim.field_value
        
        # Fallback - this should come from the job context in practice
        return "Unknown Restaurant"


# ============================================================================
# UTILITY FUNCTIONS  
# ============================================================================

def run_consensus_analysis(
    claims: List[AgentClaim], 
    venue_type: str = 'default',
    config: Optional[ConsensusConfig] = None
) -> ConsensusResult:
    """
    Convenience function to run full consensus analysis
    
    Args:
        claims: Agent claims to analyze
        venue_type: Type of venue for recency weighting
        config: Custom consensus configuration
        
    Returns:
        Complete consensus result with confidence scoring
    """
    engine = ConsensusEngine(config)
    return engine.compute_consensus(claims, venue_type)


def validate_consensus_result(result: ConsensusResult) -> List[str]:
    """
    Validate consensus result and return any issues found
    
    Args:
        result: Consensus result to validate
        
    Returns:
        List of validation warnings/errors
    """
    issues = []
    
    # Check confidence scores
    if result.overall_confidence < 0.5:
        issues.append("Very low overall confidence - consider getting more data")
    
    if result.completeness_score < 0.4:
        issues.append("Very low completeness - many fields missing")
    
    # Check field confidences
    low_confidence_fields = [
        fc.field_path for fc in result.field_confidences 
        if fc.confidence < 0.6
    ]
    
    if low_confidence_fields:
        issues.append(f"Low confidence fields: {', '.join(low_confidence_fields[:5])}")
    
    # Check source diversity
    if result.source_diversity < 2:
        issues.append("Low source diversity - consider additional data sources")
    
    return issues


# Make imports work
import re

# Export main functions
__all__ = [
    'ConsensusEngine',
    'ConsensusConfig', 
    'run_consensus_analysis',
    'validate_consensus_result'
]