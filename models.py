from typing import List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field


# =========================
# Literals
# =========================

MessageType = Literal[
    "analysis",
    "follow_up",
    "clarification",
    "out_of_scope"
]

Severity = Literal["low", "medium", "high"]

RiskLevel = Literal["low", "medium", "high"]

ProcessingLevel = Literal[
    "Minimally Processed",
    "Processed",
    "Ultra-Processed"
]

IngredientCategory = Literal[
    "Preservative",
    "Emulsifier",
    "Sweetener",
    "Artificial Color",
    "Flavor Enhancer",
    "Oil/Fat",
    "Protein Source",
    "Stabilizer",
    "Whole Food Ingredient",
    "Fortified Nutrient",
    "Thickener"
]

AnalysisType = Literal["new", "follow_up"]

EvidenceLevel = Literal[
    "strong",
    "moderate",
    "limited"
]

Allergen = Literal[
    "Milk",
    "Soy",
    "Gluten",
    "Nuts",
    "Eggs",
    "Sesame",
    "Shellfish"
]


# =========================
# Base Block
# =========================

class BaseBlock(BaseModel):
    id: Optional[str] = None
    type: str


# =========================
# Blocks
# =========================

class TextBlock(BaseBlock):
    type: Literal["text"] = "text"
    content: str


class BulletListBlock(BaseBlock):
    type: Literal["bullet_list"] = "bullet_list"
    title: str
    items: List[str]


class WarningBlock(BaseBlock):
    type: Literal["warning"] = "warning"
    severity: Severity
    evidence_level: Optional[EvidenceLevel] = None
    content: str


class ScoreBlock(BaseBlock):
    type: Literal["score"] = "score"
    label: Literal["Health Score"] = "Health Score"
    value: int = Field(..., ge=0, le=100)
    explanation: str


class IngredientBlock(BaseBlock):
    type: Literal["ingredient"] = "ingredient"

    name: str
    category: Optional[IngredientCategory] = None
    risk_level: RiskLevel
    purpose: Optional[str] = None
    explanation: str
    confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1
    )


class AllergensBlock(BaseBlock):
    type: Literal["allergens"] = "allergens"
    items: List[Allergen]


class ProcessingBlock(BaseBlock):
    type: Literal["processing"] = "processing"
    level: ProcessingLevel
    reason: str


class TableBlock(BaseBlock):
    type: Literal["table"] = "table"
    headers: List[str]
    rows: List[List[str]]


class ComparisonBlock(BaseBlock):
    type: Literal["comparison"] = "comparison"
    headers: List[str]
    rows: List[List[str]]


# =========================
# Discriminated Union
# =========================

PulseBlock = Annotated[
    Union[
        TextBlock,
        BulletListBlock,
        WarningBlock,
        ScoreBlock,
        IngredientBlock,
        AllergensBlock,
        ProcessingBlock,
        TableBlock,
        ComparisonBlock
    ],
    Field(discriminator="type")
]


# =========================
# Metadata
# =========================

class PulseMetadata(BaseModel):
    product_name: Optional[str] = None
    user_preferences: Optional[List[str]] = None
    analysis_type: Optional[AnalysisType] = None
    confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1
    )


# =========================
# Root Response
# =========================

class PulseResponse(BaseModel):
    schema_version: Optional[str] = None
    message_type: MessageType
    blocks: List[PulseBlock]
    metadata: PulseMetadata = Field(
        default_factory=PulseMetadata
    )