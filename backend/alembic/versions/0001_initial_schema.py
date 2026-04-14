"""Initial schema: papers, authors, journals, extractions, jobs

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE paper_status AS ENUM ('uploaded','parsing','parsed','extracting','extracted','review_needed','failed')")
    op.execute("CREATE TYPE extraction_status AS ENUM ('pending','complete','partial','failed','needs_review')")
    op.execute("CREATE TYPE job_status AS ENUM ('queued','running','success','failed','retrying','cancelled')")
    op.execute("CREATE TYPE job_type AS ENUM ('parse_pdf','extract_llm','generate_outputs','full_pipeline','folder_scan')")

    # ── Journals ───────────────────────────────────────────────────────────────
    op.create_table(
        "journals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False, unique=True),
        sa.Column("abbreviation", sa.String(128)),
        sa.Column("issn", sa.String(32)),
        sa.Column("eissn", sa.String(32)),
        sa.Column("publisher", sa.String(256)),
        sa.Column("impact_factor", sa.Float),
        sa.Column("impact_factor_year", sa.Integer),
        sa.Column("impact_factor_source", sa.String(256)),
        sa.Column("impact_factor_status", sa.String(32), server_default="unresolved"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_journals_name", "journals", ["name"])

    # ── Papers ─────────────────────────────────────────────────────────────────
    op.create_table(
        "papers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("file_hash_sha256", sa.String(64)),
        sa.Column("page_count", sa.Integer),
        sa.Column("status", postgresql.ENUM("uploaded","parsing","parsed","extracting","extracted","review_needed","failed", name="paper_status", create_type=False), nullable=False, server_default="uploaded"),
        sa.Column("parse_error", sa.Text),
        sa.Column("extraction_error", sa.Text),
        sa.Column("title", sa.Text),
        sa.Column("doi", sa.String(256)),
        sa.Column("abstract", sa.Text),
        sa.Column("publication_year", sa.Integer),
        sa.Column("keywords", postgresql.JSONB),
        sa.Column("volume", sa.String(64)),
        sa.Column("issue", sa.String(64)),
        sa.Column("pages", sa.String(64)),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journals.id")),
        sa.Column("summary_path", sa.String(1024)),
        sa.Column("extraction_json_path", sa.String(1024)),
        sa.Column("raw_text", sa.Text),
        sa.Column("parse_method", sa.String(32)),
        sa.Column("schema_version", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_papers_id", "papers", ["id"])
    op.create_index("ix_papers_status", "papers", ["status"])
    op.create_index("ix_papers_doi", "papers", ["doi"])
    op.create_index("ix_papers_file_hash_sha256", "papers", ["file_hash_sha256"])
    op.create_index("ix_papers_publication_year", "papers", ["publication_year"])
    op.create_index("ix_papers_journal_id", "papers", ["journal_id"])

    # ── Authors ────────────────────────────────────────────────────────────────
    op.create_table(
        "authors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(512), nullable=False),
        sa.Column("first_name", sa.String(256)),
        sa.Column("last_name", sa.String(256)),
        sa.Column("orcid", sa.String(64), unique=True),
        sa.Column("affiliation", sa.String(1024)),
        sa.Column("email", sa.String(256)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_authors_full_name", "authors", ["full_name"])

    # ── Paper Authors ──────────────────────────────────────────────────────────
    op.create_table(
        "paper_authors",
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_corresponding", sa.Boolean, server_default="false"),
    )

    # ── Extraction Records ─────────────────────────────────────────────────────
    op.create_table(
        "extraction_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("llm_model", sa.String(128)),
        sa.Column("llm_prompt_version", sa.String(32)),
        sa.Column("is_canonical", sa.Boolean, server_default="true"),
        sa.Column("status", postgresql.ENUM("pending","complete","partial","failed","needs_review", name="extraction_status", create_type=False), server_default="pending"),
        sa.Column("summary_text", sa.Text),
        sa.Column("main_findings", sa.Text),
        sa.Column("claimed_mechanism", sa.Text),
        sa.Column("limitations", sa.Text),
        sa.Column("notable_novelty", sa.Text),
        sa.Column("relevant_for_optimization", sa.Boolean),
        sa.Column("raw_llm_response", postgresql.JSONB),
        sa.Column("bibliographic_info", postgresql.JSONB),
        sa.Column("journal_quality", postgresql.JSONB),
        sa.Column("input_variables", postgresql.JSONB),
        sa.Column("output_variables", postgresql.JSONB),
        sa.Column("contextual_notes", postgresql.JSONB),
        sa.Column("reviewed_by", sa.String(256)),
        sa.Column("review_notes", sa.Text),
        sa.Column("human_edited", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_extraction_records_paper_id", "extraction_records", ["paper_id"])
    op.create_index("ix_extraction_records_is_canonical", "extraction_records", ["is_canonical"])

    # ── Material Entities ──────────────────────────────────────────────────────
    op.create_table(
        "material_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("extraction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extraction_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(512)),
        sa.Column("composition", sa.String(512)),
        sa.Column("stoichiometry", sa.String(256)),
        sa.Column("dopants", postgresql.JSONB),
        sa.Column("substrate", sa.String(256)),
        sa.Column("layer_stack", sa.Text),
        sa.Column("device_structure", sa.Text),
        sa.Column("crystal_structure", sa.String(256)),
        sa.Column("phase", sa.String(128)),
        sa.Column("dimensionality", sa.String(128)),
        sa.Column("morphology", sa.String(256)),
        sa.Column("additional_properties", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_material_entities_extraction_id", "material_entities", ["extraction_id"])

    # ── Process Conditions ─────────────────────────────────────────────────────
    op.create_table(
        "process_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("extraction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extraction_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parameter_name", sa.String(256), nullable=False),
        sa.Column("value_numeric", sa.Float),
        sa.Column("value_text", sa.String(512)),
        sa.Column("unit", sa.String(64)),
        sa.Column("variable_role", sa.String(32), server_default="input"),
        sa.Column("confidence", sa.Float),
        sa.Column("is_inferred", sa.Boolean, server_default="false"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_process_conditions_extraction_id", "process_conditions", ["extraction_id"])

    # ── Measurement Methods ────────────────────────────────────────────────────
    op.create_table(
        "measurement_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("extraction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extraction_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technique_name", sa.String(256), nullable=False),
        sa.Column("category", sa.String(128)),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Result Properties ──────────────────────────────────────────────────────
    op.create_table(
        "result_properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("extraction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extraction_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_name", sa.String(256), nullable=False),
        sa.Column("value_numeric", sa.Float),
        sa.Column("value_min", sa.Float),
        sa.Column("value_max", sa.Float),
        sa.Column("value_text", sa.String(512)),
        sa.Column("unit", sa.String(64)),
        sa.Column("conditions", sa.Text),
        sa.Column("variable_role", sa.String(32), server_default="output"),
        sa.Column("confidence", sa.Float),
        sa.Column("is_inferred", sa.Boolean, server_default="false"),
        sa.Column("needs_review", sa.Boolean, server_default="false"),
        sa.Column("material_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("material_entities.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_result_properties_extraction_id", "result_properties", ["extraction_id"])
    op.create_index("ix_result_properties_property_name", "result_properties", ["property_name"])

    # ── Source Evidence ────────────────────────────────────────────────────────
    op.create_table(
        "source_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("extraction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extraction_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(256), nullable=False),
        sa.Column("field_value", sa.Text),
        sa.Column("source_text", sa.Text),
        sa.Column("page_numbers", postgresql.JSONB),
        sa.Column("section", sa.String(256)),
        sa.Column("confidence", sa.Float),
        sa.Column("is_inferred", sa.Boolean, server_default="false"),
        sa.Column("inference_reasoning", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_source_evidences_extraction_id", "source_evidences", ["extraction_id"])

    # ── Processing Jobs ────────────────────────────────────────────────────────
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE")),
        sa.Column("celery_task_id", sa.String(256)),
        sa.Column("job_type", postgresql.ENUM("parse_pdf","extract_llm","generate_outputs","full_pipeline","folder_scan", name="job_type", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM("queued","running","success","failed","retrying","cancelled", name="job_status", create_type=False), server_default="queued"),
        sa.Column("progress_percent", sa.Float),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("max_retries", sa.Integer, server_default="3"),
        sa.Column("error_message", sa.Text),
        sa.Column("result_summary", postgresql.JSONB),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_processing_jobs_paper_id", "processing_jobs", ["paper_id"])
    op.create_index("ix_processing_jobs_celery_task_id", "processing_jobs", ["celery_task_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("processing_jobs")
    op.drop_table("source_evidences")
    op.drop_table("result_properties")
    op.drop_table("measurement_methods")
    op.drop_table("process_conditions")
    op.drop_table("material_entities")
    op.drop_table("extraction_records")
    op.drop_table("paper_authors")
    op.drop_table("authors")
    op.drop_table("papers")
    op.drop_table("journals")
    op.execute("DROP TYPE IF EXISTS job_type")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS extraction_status")
    op.execute("DROP TYPE IF EXISTS paper_status")
