import argparse
import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Callable

import pymupdf
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import (
    AnalysisInput,
    ContentAnalyzer,
    ContentAnalyzerConfig,
    ContentFieldDefinition,
    ContentFieldSchema,
    ContentFieldType,
    GenerationMethod,
    LabeledDataKnowledgeSource,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

DOCUMENT_ANALYZER_ID = "document_validation_poc_v4_official_reference"
SIGNATURE_ANALYZER_ID = "signature_image_poc_v1"


def _credential() -> AzureKeyCredential | DefaultAzureCredential:
    key = os.getenv("CONTENTUNDERSTANDING_KEY")
    if key:
        return AzureKeyCredential(key)
    return DefaultAzureCredential()


def create_client(endpoint: str) -> ContentUnderstandingClient:
    return ContentUnderstandingClient(endpoint=endpoint, credential=_credential())


def _knowledge_sources() -> list[LabeledDataKnowledgeSource]:
    container_url = os.getenv("CONTENTUNDERSTANDING_TRAINING_DATA_SAS_URL")
    if not container_url:
        raise RuntimeError(
            "Set CONTENTUNDERSTANDING_TRAINING_DATA_SAS_URL to create the "
            "official-reference analyzer."
        )

    source = LabeledDataKnowledgeSource(
        container_url=container_url,
        file_list_path="",
    )
    prefix = os.getenv("CONTENTUNDERSTANDING_TRAINING_DATA_PREFIX")
    if prefix:
        source.prefix = prefix
    return [source]


def _build_analyzer() -> ContentAnalyzer:
    fields = {
        "document_type": ContentFieldDefinition(
            type=ContentFieldType.STRING,
            method=GenerationMethod.CLASSIFY,
            enum=[
                "bank_certificate",
                "compliance_letter",
                "tax_registration_certificate",
                "chamber_of_commerce_certificate",
                "other",
            ],
            description="The business document type, based on both text and visual layout.",
        ),
        "electronic_signature_present": ContentFieldDefinition(
            type=ContentFieldType.BOOLEAN,
            method=GenerationMethod.GENERATE,
            description=(
                "True only when the document contains a digital signature panel, "
                "certificate, verification QR code, or explicit electronically-signed "
                "notice. A scanned handwritten mark alone is not electronic."
            ),
            estimate_source_and_confidence=True,
        ),
        "letterhead_present": ContentFieldDefinition(
            type=ContentFieldType.BOOLEAN,
            method=GenerationMethod.GENERATE,
            description=(
                "True when the document has company or institution branding used as "
                "letterhead, such as a logo with company name or branded header/footer. "
                "A company name appearing only in body text is not letterhead."
            ),
            estimate_source_and_confidence=True,
        ),
        "letterhead_company": ContentFieldDefinition(
            type=ContentFieldType.STRING,
            method=GenerationMethod.EXTRACT,
            description=(
                "Company or institution named in the letterhead. Return an empty string "
                "when no letterhead is present."
            ),
            estimate_source_and_confidence=True,
        ),
        "visual_consistency": ContentFieldDefinition(
            type=ContentFieldType.STRING,
            method=GenerationMethod.CLASSIFY,
            enum=["consistent", "suspicious", "inconclusive"],
            description=(
                "Assess whether the visual layout, branding, typography, identifiers, "
                "and expected sections are consistent with the classified document type. "
                "Use suspicious for concrete visual anomalies and inconclusive when the "
                "image quality or evidence is insufficient. This is not proof of authenticity."
            ),
        ),
        "visual_findings": ContentFieldDefinition(
            type=ContentFieldType.STRING,
            method=GenerationMethod.GENERATE,
            description=(
                "Concise evidence for the visual_consistency result. Mention expected "
                "elements found or missing and any visible anomalies. Do not claim "
                "forensic proof or verify cryptographic signatures."
            ),
            estimate_source_and_confidence=True,
        ),
    }
    return ContentAnalyzer(
        base_analyzer_id="prebuilt-document",
        description="POC for signatures, letterhead, and document visual consistency.",
        config=ContentAnalyzerConfig(
            enable_layout=True,
            enable_ocr=True,
            estimate_field_source_and_confidence=True,
            return_details=True,
        ),
        field_schema=ContentFieldSchema(
            name="document_validation",
            description="Visual validation signals for supplier documents.",
            fields=fields,
        ),
        models={
            "completion": "gpt-5.4-mini",
            "embedding": "text-embedding-3-small",
        },
        knowledge_sources=_knowledge_sources(),
    )


def _build_signature_analyzer() -> ContentAnalyzer:
    return ContentAnalyzer(
        base_analyzer_id="prebuilt-image",
        description="Detect visible handwritten signatures in rendered document pages.",
        field_schema=ContentFieldSchema(
            name="signature_detection",
            fields={
                "handwritten_signature_present": ContentFieldDefinition(
                    type=ContentFieldType.BOOLEAN,
                    method=GenerationMethod.GENERATE,
                    description=(
                        "True when the image contains at least one visible ink-like "
                        "cursive stroke, scribble, or hand-drawn signature mark. Include "
                        "scanned signatures and signatures overlapped by stamps or "
                        "printed text. Do not require OCR readability."
                    ),
                    estimate_source_and_confidence=True,
                ),
                "handwritten_signature_count": ContentFieldDefinition(
                    type=ContentFieldType.INTEGER,
                    method=GenerationMethod.GENERATE,
                    description=(
                        "Count visible handwritten signature marks. Include scanned "
                        "cursive signatures even when stamps or text overlap them."
                    ),
                    estimate_source_and_confidence=True,
                ),
                "signature_evidence": ContentFieldDefinition(
                    type=ContentFieldType.STRING,
                    method=GenerationMethod.GENERATE,
                    description=(
                        "Briefly describe the visible handwritten signature evidence "
                        "and location. Return an empty string when there is none."
                    ),
                    estimate_source_and_confidence=True,
                ),
            },
        ),
        models={"completion": "gpt-5.4-mini"},
    )


def _ensure_analyzer(
    client: ContentUnderstandingClient,
    analyzer_id: str,
    analyzer_builder: Callable[[], ContentAnalyzer],
) -> None:
    try:
        client.get_analyzer(analyzer_id=analyzer_id)
    except ResourceNotFoundError:
        client.begin_create_analyzer(
            analyzer_id=analyzer_id,
            resource=analyzer_builder(),
        ).result()


def prepare_analyzers(client: ContentUnderstandingClient) -> None:
    _ensure_analyzer(client, DOCUMENT_ANALYZER_ID, _build_analyzer)
    _ensure_analyzer(
        client,
        SIGNATURE_ANALYZER_ID,
        _build_signature_analyzer,
    )


def _field_to_dict(field: Any) -> dict[str, Any]:
    raw = field.as_dict()
    value_keys = (
        "valueString",
        "valueBoolean",
        "valueDate",
        "valueTime",
        "valueNumber",
        "valueInteger",
        "valueArray",
        "valueObject",
        "valueJson",
    )
    value = next((raw[key] for key in value_keys if key in raw), None)
    result: dict[str, Any] = {"value": value}
    confidence = raw.get("confidence")
    source = raw.get("source")
    if confidence is not None:
        result["confidence"] = confidence
    if source:
        result["source"] = source
    return result


def _analyze_signatures(
    client: ContentUnderstandingClient, document_path: Path
) -> dict[str, Any]:
    count = 0
    evidence = []
    with pymupdf.open(document_path) as document:
        for page_number, page in enumerate(document, start=1):
            image = page.get_pixmap(
                matrix=pymupdf.Matrix(2.0, 2.0),
                alpha=False,
            ).tobytes("png")
            analysis = client.begin_analyze(
                analyzer_id=SIGNATURE_ANALYZER_ID,
                inputs=[
                    AnalysisInput(
                        data=image,
                        name=f"{document_path.stem}-page-{page_number}.png",
                        mime_type="image/png",
                    )
                ],
            ).result()
            if not analysis.contents:
                raise RuntimeError(
                    f"Signature analyzer returned no content for page {page_number}."
                )

            fields = analysis.contents[0].fields or {}
            count_field = fields.get("handwritten_signature_count")
            present_field = fields.get("handwritten_signature_present")
            page_count = (
                _field_to_dict(count_field)["value"] if count_field else None
            )
            if isinstance(page_count, int):
                count += page_count
            elif present_field and _field_to_dict(present_field)["value"] is True:
                count += 1

            evidence_field = fields.get("signature_evidence")
            page_evidence = (
                _field_to_dict(evidence_field)["value"] if evidence_field else None
            )
            if page_evidence:
                evidence.append(f"Page {page_number}: {page_evidence}")

    return {
        "handwritten_signature_present": {"value": count > 0},
        "signature_evidence": {"value": " ".join(evidence)},
    }


def _signature_type(handwritten: bool, electronic: bool | None) -> str:
    if handwritten and electronic:
        return "both"
    if handwritten:
        return "handwritten"
    if electronic:
        return "electronic"
    if electronic is False:
        return "none"
    return "inconclusive"


def _review_required(fields: dict[str, Any]) -> bool:
    def value(name: str) -> Any:
        return fields.get(name, {}).get("value")

    return not (
        value("document_type")
        and value("signature_type") in {"handwritten", "electronic", "both"}
        and value("letterhead_present") is True
        and value("visual_consistency") == "consistent"
    )


def analyze_document(
    client: ContentUnderstandingClient,
    document_path: Path,
    include_handwritten_signatures: bool = True,
) -> dict[str, Any]:
    if not document_path.is_file():
        raise FileNotFoundError(f"Document not found: {document_path}")

    mime_type = mimetypes.guess_type(document_path.name)[0] or "application/octet-stream"
    analysis = client.begin_analyze(
        analyzer_id=DOCUMENT_ANALYZER_ID,
        inputs=[
            AnalysisInput(
                data=document_path.read_bytes(),
                name=document_path.name,
                mime_type=mime_type,
            )
        ],
    ).result()

    if not analysis.contents:
        raise RuntimeError("Content Understanding returned no document content.")

    fields = analysis.contents[0].fields or {}
    formatted_fields = {
        name: _field_to_dict(field) for name, field in fields.items()
    }
    if include_handwritten_signatures:
        signature_fields = _analyze_signatures(client, document_path)
        handwritten = signature_fields["handwritten_signature_present"]["value"]
        electronic = formatted_fields.pop(
            "electronic_signature_present",
            {"value": None},
        )["value"]
        signature_fields["signature_type"] = {
            "value": _signature_type(handwritten, electronic)
        }
        formatted_fields.update(signature_fields)

    formatted_fields["review_required"] = {
        "value": _review_required(formatted_fields)
    }

    return {
        "file": document_path.name,
        "analyzer_ids": [DOCUMENT_ANALYZER_ID, SIGNATURE_ANALYZER_ID],
        "fields": formatted_fields,
    }


def validate_document(endpoint: str, document_path: Path) -> dict[str, Any]:
    client = create_client(endpoint)
    prepare_analyzers(client)
    return analyze_document(client, document_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze signature, letterhead, and visual consistency signals."
    )
    parser.add_argument("document", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    endpoint = os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
    if not endpoint:
        parser.error("Set CONTENTUNDERSTANDING_ENDPOINT before running the POC.")

    result = validate_document(endpoint, args.document)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
