"""
GPT-5 Happy Hour Discovery System - Core Data Models
Canonical Restaurant Input (CRI) and validation system with Pydantic

This module defines the standardized data structures that all agents use,
ensuring type safety, validation, and consistent data processing across
the entire system.
"""

from datetime import datetime, time, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Union, Literal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel, 
    Field, 
    validator, 
    root_validator,
    HttpUrl,
    EmailStr,
    constr,
    confloat,
    conint
)
from pydantic.types import StrictStr
import phonenumbers
import re


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class AgentType(str, Enum):
    """Types of agents in the system"""
    ORCHESTRATOR = "orchestrator"
    SITE_AGENT = "site_agent"
    GOOGLE_AGENT = "google_agent"
    YELP_AGENT = "yelp_agent"
    VOICE_VERIFY = "voice_verify"
    SOCIAL_AGENT = "social_agent"
    CONSENSUS_ENGINE = "consensus_engine"


class SourceType(str, Enum):
    """Types of data sources agents can extract from"""
    WEBSITE = "website"
    GOOGLE_POST = "google_post"
    GOOGLE_QA = "google_qa"
    GOOGLE_REVIEW = "google_review"
    YELP_REVIEW = "yelp_review"
    YELP_PHOTO = "yelp_photo"
    INSTAGRAM_POST = "instagram_post"
    INSTAGRAM_COMMENT = "instagram_comment"
    FACEBOOK_POST = "facebook_post"
    PHONE_CALL = "phone_call"
    EMAIL = "email"
    MENU_PDF = "menu_pdf"
    RESY_EVENT = "resy_event"
    OPENTABLE_EVENT = "opentable_event"
    UNTAPPD_MENU = "untappd_menu"
    BEERMENU = "beermenu"


class HappyHourStatus(str, Enum):
    """Happy hour availability status"""
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    SEASONAL = "seasonal"
    UNKNOWN = "unknown"
    NO_HAPPY_HOUR = "no_happy_hour"


class JobStatus(str, Enum):
    """Status of an analysis job"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DayOfWeek(str, Enum):
    """Days of the week (lowercase for consistency)"""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class OfferCategory(str, Enum):
    """Categories of happy hour offers"""
    BEER = "beer"
    WINE = "wine"
    COCKTAIL = "cocktail"
    SPIRITS = "spirits"
    FOOD_APPETIZER = "food_appetizer"
    FOOD_MAIN = "food_main"
    FOOD_DESSERT = "food_dessert"
    OTHER = "other"


class Specificity(str, Enum):
    """How specific/precise an agent claim is"""
    EXACT = "exact"              # "3:00pm - 6:00pm"
    APPROXIMATE = "approximate"   # "around 3-6pm"
    VAGUE = "vague"              # "afternoon"
    IMPLIED = "implied"          # "after work specials"


class Modality(str, Enum):
    """How information was extracted"""
    TEXT = "text"                # Plain text extraction
    IMAGE_OCR = "image_ocr"      # OCR from images/PDFs
    VOICE = "voice"              # Phone call transcript
    STRUCTURED_DATA = "structured_data"  # API response


# ============================================================================
# CORE LOCATION & CONTACT MODELS
# ============================================================================

class PhoneNumber(BaseModel):
    """Validated phone number with international format"""
    raw: str = Field(..., description="Original phone number as entered")
    e164: Optional[str] = Field(None, description="Standardized E.164 format (+1234567890)")
    national: Optional[str] = Field(None, description="National format (123) 456-7890")
    country_code: Optional[str] = Field(None, description="2-letter country code")
    is_valid: bool = Field(False, description="Whether phone number is valid")
    
    @validator('e164', 'national', pre=True, always=True)
    def parse_phone_number(cls, v, values):
        raw_phone = values.get('raw', '')
        if not raw_phone:
            return None
            
        try:
            parsed = phonenumbers.parse(raw_phone, 'US')  # Default to US
            
            if phonenumbers.is_valid_number(parsed):
                if v is None:  # Setting e164
                    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                else:  # Setting national
                    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
            return None
        except phonenumbers.NumberParseException:
            return None
    
    @validator('country_code', pre=True, always=True)
    def set_country_code(cls, v, values):
        raw_phone = values.get('raw', '')
        if not raw_phone:
            return None
            
        try:
            parsed = phonenumbers.parse(raw_phone, 'US')
            return phonenumbers.region_code_for_number(parsed)
        except phonenumbers.NumberParseException:
            return None
    
    @validator('is_valid', pre=True, always=True)
    def validate_phone(cls, v, values):
        raw_phone = values.get('raw', '')
        if not raw_phone:
            return False
            
        try:
            parsed = phonenumbers.parse(raw_phone, 'US')
            return phonenumbers.is_valid_number(parsed)
        except phonenumbers.NumberParseException:
            return False


class Address(BaseModel):
    """Structured address with normalization"""
    raw: str = Field(..., description="Full address as provided")
    street_number: Optional[str] = Field(None, description="Street number")
    street_name: Optional[str] = Field(None, description="Street name")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State/province")
    postal_code: Optional[str] = Field(None, description="ZIP/postal code")
    country: str = Field('US', description="Country code")
    
    # Normalized components for matching
    normalized: Optional[str] = Field(None, description="Normalized address for comparison")
    
    @validator('normalized', pre=True, always=True)
    def normalize_address(cls, v, values):
        raw_address = values.get('raw', '')
        if not raw_address:
            return None
        
        # Basic normalization (could be enhanced with libpostal)
        normalized = raw_address.upper()
        normalized = re.sub(r'\b(STREET|ST)\b', 'ST', normalized)
        normalized = re.sub(r'\b(AVENUE|AVE)\b', 'AVE', normalized)
        normalized = re.sub(r'\b(BOULEVARD|BLVD)\b', 'BLVD', normalized)
        normalized = re.sub(r'\b(ROAD|RD)\b', 'RD', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()


class GeographicCoordinates(BaseModel):
    """Geographic coordinates with validation"""
    latitude: confloat(ge=-90, le=90) = Field(..., description="Latitude (-90 to 90)")
    longitude: confloat(ge=-180, le=180) = Field(..., description="Longitude (-180 to 180)")
    accuracy_meters: Optional[conint(ge=0)] = Field(None, description="Accuracy in meters")
    source: Optional[str] = Field(None, description="Source of coordinates (geocoder, manual, etc.)")


class PlatformIdentifiers(BaseModel):
    """External platform identifiers for multi-source lookups"""
    google_place_id: Optional[constr(min_length=10)] = Field(None, description="Google Places ID")
    yelp_business_id: Optional[str] = Field(None, description="Yelp business ID")
    facebook_page_id: Optional[str] = Field(None, description="Facebook page ID")
    instagram_handle: Optional[constr(pattern=r'^@?[a-zA-Z0-9_.]+$')] = Field(None, description="Instagram handle")
    twitter_handle: Optional[constr(pattern=r'^@?[a-zA-Z0-9_]+$')] = Field(None, description="Twitter handle")
    resy_slug: Optional[str] = Field(None, description="Resy restaurant slug")
    opentable_slug: Optional[str] = Field(None, description="OpenTable restaurant slug")
    foursquare_id: Optional[str] = Field(None, description="Foursquare venue ID")
    
    @validator('instagram_handle', 'twitter_handle', pre=True)
    def normalize_social_handles(cls, v):
        if v and not v.startswith('@'):
            return f'@{v}'
        return v


# ============================================================================
# CANONICAL RESTAURANT INPUT (CRI) - THE CORE MODEL
# ============================================================================

class CanonicalRestaurantInput(BaseModel):
    """
    Canonical Restaurant Input (CRI) - The standardized restaurant entity
    that all agents work with. This ensures consistency and type safety
    across the entire system.
    """
    
    # Core identification
    name: constr(min_length=1, max_length=200) = Field(..., description="Restaurant name (required)")
    address: Optional[Address] = Field(None, description="Full address details")
    phone: Optional[PhoneNumber] = Field(None, description="Contact phone number")
    website: Optional[HttpUrl] = Field(None, description="Official website URL")
    email: Optional[EmailStr] = Field(None, description="Contact email address")
    
    # Geographic data
    coordinates: Optional[GeographicCoordinates] = Field(None, description="Lat/lng coordinates")
    timezone: Optional[str] = Field('America/Los_Angeles', description="IANA timezone identifier")
    
    # Platform identifiers for agent lookup
    platform_ids: Optional[PlatformIdentifiers] = Field(default_factory=PlatformIdentifiers)
    
    # Business metadata
    business_type: Optional[str] = Field(None, description="Type of establishment")
    cuisine_type: List[str] = Field(default_factory=list, description="Cuisine categories")
    price_range: Optional[Literal['$', '$$', '$$$', '$$$$']] = Field(None, description="Price range")
    
    # Hints for agents (optional context)
    neighborhood: Optional[str] = Field(None, description="Neighborhood/area")
    known_for: List[str] = Field(default_factory=list, description="What restaurant is known for")
    target_demographic: Optional[str] = Field(None, description="Primary customer base")
    
    # System metadata
    cri_id: UUID = Field(default_factory=uuid4, description="Unique CRI identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = Field(None, description="How this CRI was created")
    confidence: confloat(ge=0.0, le=1.0) = Field(0.5, description="Confidence in data accuracy")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            UUID: lambda uuid: str(uuid),
            Decimal: lambda d: float(d)
        }
        schema_extra = {
            "example": {
                "name": "The Waterfront Bar & Grill",
                "address": {
                    "raw": "2044 Kettner Blvd, San Diego, CA 92101",
                    "city": "San Diego",
                    "state": "CA",
                    "postal_code": "92101"
                },
                "phone": {
                    "raw": "(619) 555-1212"
                },
                "website": "https://waterfrontbarandgrill.com",
                "coordinates": {
                    "latitude": 32.72421,
                    "longitude": -117.16915
                },
                "platform_ids": {
                    "google_place_id": "ChIJ...",
                    "yelp_business_id": "waterfront-san-diego",
                    "instagram_handle": "@waterfrontbar"
                },
                "cuisine_type": ["American", "Seafood"],
                "price_range": "$$",
                "neighborhood": "Little Italy"
            }
        }


# ============================================================================
# HAPPY HOUR DATA MODELS
# ============================================================================

class TimeSlot(BaseModel):
    """A time range for happy hour"""
    start: time = Field(..., description="Start time (24-hour format)")
    end: time = Field(..., description="End time (24-hour format)")
    notes: Optional[str] = Field(None, description="Additional notes about this time slot")
    
    @root_validator(skip_on_failure=True)
    def validate_time_range(cls, values):
        start_time = values.get('start')
        end_time = values.get('end')
        
        if start_time and end_time and start_time >= end_time:
            raise ValueError("Start time must be before end time")
        return values


class DailySchedule(BaseModel):
    """Happy hour schedule for a single day"""
    day: DayOfWeek = Field(..., description="Day of the week")
    time_slots: List[TimeSlot] = Field(default_factory=list, description="Time ranges for happy hour")
    special_notes: Optional[str] = Field(None, description="Special conditions for this day")
    
    @property
    def has_happy_hour(self) -> bool:
        """Whether this day has any happy hour time slots"""
        return len(self.time_slots) > 0


class HappyHourOffer(BaseModel):
    """A specific happy hour offer (drink or food item)"""
    category: OfferCategory = Field(..., description="Category of offer")
    item_name: str = Field(..., description="Name of the item")
    regular_price: Optional[Decimal] = Field(None, description="Regular price")
    happy_hour_price: Optional[Decimal] = Field(None, description="Happy hour price")
    discount_percentage: Optional[conint(ge=0, le=100)] = Field(None, description="Percentage discount")
    description: Optional[str] = Field(None, description="Additional details")
    restrictions: List[str] = Field(default_factory=list, description="Any restrictions or conditions")
    
    @root_validator(skip_on_failure=True)
    def validate_pricing(cls, values):
        regular = values.get('regular_price')
        happy_hour = values.get('happy_hour_price')
        discount = values.get('discount_percentage')
        
        # Ensure at least some pricing information is provided
        if not any([regular, happy_hour, discount]):
            raise ValueError("Must provide at least one pricing field")
        
        # Validate happy hour price is less than regular price
        if regular and happy_hour and happy_hour >= regular:
            raise ValueError("Happy hour price must be less than regular price")
        
        return values


class HappyHourSchedule(BaseModel):
    """Complete happy hour schedule and details"""
    status: HappyHourStatus = Field(..., description="Overall happy hour status")
    
    # Schedule
    weekly_schedule: List[DailySchedule] = Field(default_factory=list, description="Weekly schedule")
    
    # Offers
    drink_offers: List[HappyHourOffer] = Field(default_factory=list, description="Drink specials")
    food_offers: List[HappyHourOffer] = Field(default_factory=list, description="Food specials")
    
    # Restrictions and conditions
    areas_applicable: List[str] = Field(default_factory=list, description="Where happy hour applies")
    blackout_dates: List[str] = Field(default_factory=list, description="Dates when HH is not available")
    special_conditions: List[str] = Field(default_factory=list, description="Special rules or conditions")
    dine_in_only: bool = Field(False, description="Whether happy hour is dine-in only")
    
    # Metadata
    last_verified: Optional[datetime] = Field(None, description="When this data was last verified")
    expires_at: Optional[datetime] = Field(None, description="When this data should be refreshed")
    
    @property
    def all_offers(self) -> List[HappyHourOffer]:
        """All offers (drinks + food) combined"""
        return self.drink_offers + self.food_offers
    
    @property
    def active_days(self) -> List[DayOfWeek]:
        """Days that have happy hour time slots"""
        return [schedule.day for schedule in self.weekly_schedule if schedule.has_happy_hour]


# ============================================================================
# AGENT EVIDENCE & CLAIMS
# ============================================================================

class AgentClaim(BaseModel):
    """A single piece of evidence from an agent with full provenance"""
    
    # Identification
    claim_id: UUID = Field(default_factory=uuid4, description="Unique claim identifier")
    agent_type: AgentType = Field(..., description="Which agent made this claim")
    agent_version: str = Field('1.0.0', description="Agent version for reproducibility")
    
    # Source information
    source_type: SourceType = Field(..., description="Type of source")
    source_url: Optional[HttpUrl] = Field(None, description="URL of source")
    source_domain: Optional[str] = Field(None, description="Domain for reliability weighting")
    
    # Field-specific claim
    field_path: str = Field(..., description="JSON path to field (e.g., 'schedule.monday[0].start')")
    field_value: Any = Field(..., description="The extracted value")
    
    # Evidence quality
    agent_confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Agent's confidence in this claim")
    specificity: Specificity = Field(..., description="How specific/precise this claim is")
    modality: Modality = Field(..., description="How information was extracted")
    
    # Temporal information
    observed_at: datetime = Field(..., description="When this information was valid/found")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="When we extracted it")
    
    # Evidence
    raw_snippet: Optional[str] = Field(None, description="Raw text that supports this claim")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Full API response or HTML for debugging")
    
    # Processing metadata
    processing_time_ms: Optional[conint(ge=0)] = Field(None, description="Time to extract this claim")
    cost_cents: Optional[conint(ge=0)] = Field(None, description="API cost for this claim")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            UUID: lambda uuid: str(uuid)
        }


class AgentResult(BaseModel):
    """Complete result from a single agent execution"""
    
    # Identification
    result_id: UUID = Field(default_factory=uuid4)
    agent_type: AgentType = Field(..., description="Agent that produced this result")
    cri_id: UUID = Field(..., description="CRI this result is for")
    
    # Execution metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    success: bool = Field(False, description="Whether agent executed successfully")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Results
    claims: List[AgentClaim] = Field(default_factory=list, description="All claims made by this agent")
    total_confidence: confloat(ge=0.0, le=1.0) = Field(0.0, description="Overall confidence in results")
    
    # Performance metrics
    execution_time_ms: Optional[conint(ge=0)] = Field(None, description="Total execution time")
    total_cost_cents: Optional[conint(ge=0)] = Field(None, description="Total API costs")
    sources_accessed: List[str] = Field(default_factory=list, description="URLs/sources accessed")
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Execution duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# ============================================================================
# CONSENSUS & FINAL RESULTS
# ============================================================================

class FieldConfidence(BaseModel):
    """Confidence scoring for a specific field"""
    field_path: str = Field(..., description="JSON path to field")
    field_value: Any = Field(..., description="The consensus value")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Mathematical confidence score")
    
    # Supporting evidence
    supporting_claims: List[UUID] = Field(default_factory=list, description="Claim IDs that support this value")
    conflicting_claims: List[UUID] = Field(default_factory=list, description="Claim IDs that conflict")
    
    # Consensus algorithm details
    source_weight_sum: Decimal = Field(default=Decimal('0.0'), description="Total source weights")
    recency_weight_sum: Decimal = Field(default=Decimal('0.0'), description="Total recency weights")
    specificity_bonus: Decimal = Field(default=Decimal('0.0'), description="Specificity bonuses")
    contradiction_penalty: Decimal = Field(default=Decimal('0.0'), description="Penalty for conflicts")
    
    class Config:
        json_encoders = {
            Decimal: lambda d: float(d),
            UUID: lambda uuid: str(uuid)
        }


class ConsensusResult(BaseModel):
    """Final consensus result for a restaurant with confidence scoring"""
    
    # Identification
    result_id: UUID = Field(default_factory=uuid4)
    cri_id: UUID = Field(..., description="CRI this result is for")
    venue_id: Optional[UUID] = Field(None, description="Database venue ID")
    
    # Final happy hour data
    restaurant_name: str = Field(..., description="Restaurant name")
    happy_hour_data: HappyHourSchedule = Field(..., description="Final happy hour details")
    
    # Confidence metrics
    overall_confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Overall confidence score")
    field_confidences: List[FieldConfidence] = Field(default_factory=list)
    
    # Quality metrics
    completeness_score: confloat(ge=0.0, le=1.0) = Field(0.0, description="How complete the data is")
    evidence_count: conint(ge=0) = Field(0, description="Total number of evidence pieces")
    source_diversity: conint(ge=0) = Field(0, description="Number of different source types")
    
    # Review flags
    needs_human_review: bool = Field(False, description="Whether human review is needed")
    review_reasons: List[str] = Field(default_factory=list, description="Why human review is needed")
    could_not_determine: List[str] = Field(default_factory=list, description="Fields we couldn't determine")
    
    # Metadata
    compiled_at: datetime = Field(default_factory=datetime.utcnow)
    agent_results_used: List[UUID] = Field(default_factory=list, description="Agent result IDs used")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            UUID: lambda uuid: str(uuid),
            Decimal: lambda d: float(d)
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_cri_from_dict(data: Dict[str, Any]) -> CanonicalRestaurantInput:
    """
    Create a CRI from a dictionary with smart field mapping
    Handles common input formats from CSV uploads, API calls, etc.
    """
    
    # Map common field names to CRI structure
    field_mapping = {
        'restaurant_name': 'name',
        'business_name': 'name',
        'venue_name': 'name',
        'phone_number': 'phone',
        'telephone': 'phone',
        'tel': 'phone',
        'website_url': 'website',
        'web': 'website',
        'url': 'website',
        'email_address': 'email',
        'contact_email': 'email',
        'lat': ('coordinates', 'latitude'),
        'lng': ('coordinates', 'longitude'),
        'lon': ('coordinates', 'longitude'),
        'longitude': ('coordinates', 'longitude'),
        'latitude': ('coordinates', 'latitude'),
    }
    
    # Normalize keys
    normalized_data = {}
    for key, value in data.items():
        if key in field_mapping:
            mapped_key = field_mapping[key]
            if isinstance(mapped_key, tuple):
                # Nested field
                if mapped_key[0] not in normalized_data:
                    normalized_data[mapped_key[0]] = {}
                normalized_data[mapped_key[0]][mapped_key[1]] = value
            else:
                normalized_data[mapped_key] = value
        else:
            normalized_data[key] = value
    
    # Handle phone number
    if 'phone' in normalized_data and isinstance(normalized_data['phone'], str):
        normalized_data['phone'] = {'raw': normalized_data['phone']}
    
    # Handle address
    if 'address' in normalized_data and isinstance(normalized_data['address'], str):
        normalized_data['address'] = {'raw': normalized_data['address']}
    
    return CanonicalRestaurantInput(**normalized_data)


def validate_cri(cri: CanonicalRestaurantInput) -> List[str]:
    """
    Validate a CRI and return list of warnings/issues
    Used for data quality checking before sending to agents
    """
    warnings = []
    
    # Check essential fields
    if not cri.name or len(cri.name.strip()) < 2:
        warnings.append("Restaurant name is too short or missing")
    
    if not cri.address or not cri.address.raw:
        warnings.append("Address is missing - agents may have difficulty finding venue")
    
    if not cri.phone or not cri.phone.is_valid:
        warnings.append("Valid phone number missing - VoiceVerify agent will be skipped")
    
    if not cri.website:
        warnings.append("Website missing - SiteAgent will be limited")
    
    # Check data quality
    if cri.confidence < 0.3:
        warnings.append("Low confidence in input data quality")
    
    if not cri.coordinates:
        warnings.append("Geographic coordinates missing - location-based matching may be inaccurate")
    
    # Check platform IDs
    platform_count = sum(1 for field in cri.platform_ids.__fields__.values() 
                        if getattr(cri.platform_ids, field.name) is not None)
    if platform_count == 0:
        warnings.append("No platform IDs available - agents will rely on name/address matching only")
    
    return warnings


def estimate_agent_compatibility(cri: CanonicalRestaurantInput) -> Dict[AgentType, float]:
    """
    Estimate how compatible a CRI is with each agent type
    Returns compatibility scores (0.0 - 1.0) for cost optimization
    """
    compatibility = {}
    
    # Site Agent - needs website
    compatibility[AgentType.SITE_AGENT] = 1.0 if cri.website else 0.1
    
    # Google Agent - better with address/coordinates
    google_score = 0.5
    if cri.address and cri.address.raw:
        google_score += 0.3
    if cri.coordinates:
        google_score += 0.2
    compatibility[AgentType.GOOGLE_AGENT] = min(1.0, google_score)
    
    # Yelp Agent - better with address and platform ID
    yelp_score = 0.3
    if cri.address:
        yelp_score += 0.4
    if cri.platform_ids and cri.platform_ids.yelp_business_id:
        yelp_score += 0.3
    compatibility[AgentType.YELP_AGENT] = min(1.0, yelp_score)
    
    # Voice Verify - needs valid phone number
    compatibility[AgentType.VOICE_VERIFY] = 1.0 if (cri.phone and cri.phone.is_valid) else 0.0
    
    return compatibility


# Export main models for use in agents
__all__ = [
    'CanonicalRestaurantInput',
    'HappyHourSchedule',
    'AgentClaim',
    'AgentResult', 
    'ConsensusResult',
    'create_cri_from_dict',
    'validate_cri',
    'estimate_agent_compatibility',
    'AgentType',
    'SourceType',
    'HappyHourStatus',
    'Specificity',
    'Modality'
]