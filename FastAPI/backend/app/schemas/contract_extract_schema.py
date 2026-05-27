from pydantic import BaseModel, Field


class ExtractedContractInfo(BaseModel):
    document_id: str | None = None
    contract_type: str | None = None
    deposit_amount: int | None = None
    lease_start_date: str | None = None
    lease_end_date: str | None = None
    confirmed_date_status: str | None = None
    move_in_report_status: str | None = None
    priority_rights: str | None = None
    address: str | None = None
    landlord_name: str | None = None
    tenant_name: str | None = None
    special_terms: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)
