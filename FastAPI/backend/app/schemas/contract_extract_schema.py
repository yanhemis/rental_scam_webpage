from pydantic import BaseModel, Field
from typing import Optional


class ExtractedContractInfo(BaseModel):
    document_id: Optional[str] = None
    contract_type: Optional[str] = None
    deposit_amount: Optional[int] = None
    lease_start_date: Optional[str] = None
    lease_end_date: Optional[str] = None
    confirmed_date_status: Optional[str] = None
    move_in_report_status: Optional[str] = None
    priority_rights: Optional[str] = None
    address: Optional[str] = None
    landlord_name: Optional[str] = None
    tenant_name: Optional[str] = None
    special_terms: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)
