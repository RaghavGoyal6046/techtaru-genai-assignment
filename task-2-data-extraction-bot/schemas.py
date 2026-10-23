import re
from enum import Enum
from typing import List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    RESUME = "resume"
    INVOICE = "invoice"


class ExtractionRequest(BaseModel):
    document_type: DocumentType = Field(
        ...,
        description="Type of document: 'resume' or 'invoice'"
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Raw document text"
    )

    @field_validator("text")
    @classmethod
    def validate_non_whitespace_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Input text cannot be empty or purely whitespace.")
        return stripped


class ResumeData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: Optional[float] = None
    current_role: Optional[str] = None
    education: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip().lower()
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, cleaned):
            return None
        return cleaned


class InvoiceLineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class InvoiceData(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    vendor_name: Optional[str] = None
    client_name: Optional[str] = None
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None


class ExtractionResponse(BaseModel):
    success: bool = True
    document_type: str
    provider_used: str
    data: Union[ResumeData, InvoiceData]
    warnings: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    details: Optional[Any] = None
