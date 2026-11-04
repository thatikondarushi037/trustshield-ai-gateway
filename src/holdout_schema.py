"""Private collection schemas; validation errors must never echo submitted values."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")]
Checksum = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Label = Literal["SAFE", "SENSITIVE", "UNCERTAIN", "OUT_OF_SCOPE"]


class PrivateRow(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Record(PrivateRow):
    record_id: UUID
    text: Annotated[str, Field(min_length=1, max_length=20000)]
    source_id: UUID
    source_revision: Identifier
    collected_at: datetime
    group_namespace: Identifier
    template_family_id: Identifier
    author_group_id: Identifier
    document_group_id: Identifier
    person_group_id: Identifier
    derivation_parent_id: UUID | None = None
    language: Literal["en"]
    category: Literal["EMAIL", "PIN", "ACCOUNT", "PHONE", "ADDRESS", "CREDENTIAL", "MIXED"]
    partition: Literal["DEVELOPMENT", "HOLDOUT"]
    content_kind: Literal["FICTIONAL"]

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Blank content")
        return value

    @field_validator("collected_at")
    @classmethod
    def aware(cls, value):
        if value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value


class Source(PrivateRow):
    source_id: UUID
    revision: Identifier
    origin_kind: Literal["INDEPENDENT_AUTHOR", "LICENSED_CORPUS"]
    evidence_file: Annotated[str, Field(pattern=r"^evidence/[A-Za-z0-9_.-]+$")]
    evidence_sha256: Checksum
    license_or_consent_verified: Literal[True]
    independence_attested: Literal[True]
    repository_examples_exposure: Literal["NONE"]
    model_outputs_exposure: Literal["NONE"]
    verified_by: UUID


class Annotation(PrivateRow):
    record_id: UUID
    annotator_id: UUID
    label: Label
    guideline_version: Identifier
    independent_blind: Literal[True]
    reason_code: Literal["CONCEPT_ONLY", "OBSERVED_DISCLOSURE", "AMBIGUOUS", "OUT_OF_SCOPE"]
    annotated_at: datetime

    @field_validator("annotated_at")
    @classmethod
    def aware(cls, value):
        if value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value


class Adjudication(PrivateRow):
    record_id: UUID
    adjudicator_id: UUID
    final_label: Literal["SAFE", "SENSITIVE", "EXCLUDE"]
    guideline_version: Identifier
    reason_code: Literal["LABEL_RESOLVED", "AMBIGUOUS_EXCLUDED", "OUT_OF_SCOPE_EXCLUDED"]
    adjudicated_at: datetime

    @field_validator("adjudicated_at")
    @classmethod
    def aware(cls, value):
        if value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value


class LeakageReview(PrivateRow):
    record_id: UUID
    known_ref: Annotated[str, Field(pattern=r"^[A-Za-z0-9_./:-]{1,180}$")]
    candidate_sha256: Checksum
    known_text_sha256: Checksum
    reviewer_id: UUID
    disposition: Literal["BENIGN", "RELATED", "UNRESOLVED"]
    reason_code: Literal["DISTINCT_INTENT", "GENERIC_WORDING", "SHARED_TEMPLATE", "UNRESOLVED"]


class Collection(PrivateRow):
    version: Identifier
    state: Literal["PREPARATION", "COLLECTED_REVIEWED"]
    custodian_id: UUID | None = None
    independence_attested: bool


class Bundle(PrivateRow):
    collection: Collection
    records: list[Record]
    sources: list[Source]
    annotations: list[Annotation]
    adjudications: list[Adjudication]
    leakage_reviews: list[LeakageReview]


TABLES = {"records": Record, "sources": Source, "annotations": Annotation,
          "adjudications": Adjudication, "leakage_reviews": LeakageReview}
