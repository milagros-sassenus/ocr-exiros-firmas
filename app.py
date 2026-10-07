import os
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from document_validation import validate_document

DOCUMENT_TYPES = {
    "bank_certificate": "Certificacion bancaria",
    "compliance_letter": "Carta de cumplimiento",
    "tax_registration_certificate": "Constancia fiscal",
    "chamber_of_commerce_certificate": "Certificado de camara de comercio",
    "other": "Otro",
}

SIGNATURE_TYPES = {
    "handwritten": "Manuscrita",
    "electronic": "Electronica",
    "both": "Manuscrita y electronica",
    "none": "No detectada",
    "inconclusive": "No concluyente",
}

VISUAL_RESULTS = {
    "consistent": "Consistente",
    "suspicious": "Sospechoso",
    "inconclusive": "No concluyente",
}


def _value(fields: dict[str, Any], name: str) -> Any:
    return fields.get(name, {}).get("value")


def _boolean_result(value: bool | None) -> str:
    if value is True:
        return "Detectado"
    if value is False:
        return "No detectado"
    return "No concluyente"


def _result_messages(
    document_type: str | None,
    signature_type: str | None,
    letterhead: bool | None,
    visual: str | None,
) -> list[tuple[str, str]]:
    messages = []

    if not document_type:
        messages.append(("warning", "No se pudo identificar el tipo de documento."))

    if signature_type == "none":
        messages.append(
            ("warning", "No se detecto firma manuscrita ni electronica.")
        )
    elif signature_type in {None, "inconclusive"}:
        messages.append(("warning", "No se pudo determinar si el documento tiene firma."))

    if letterhead is False:
        messages.append(("warning", "No se detecto membrete de la compania o institucion."))
    elif letterhead is None:
        messages.append(
            ("warning", "No se pudo determinar si el documento tiene membrete.")
        )

    if visual == "suspicious":
        messages.append(
            (
                "error",
                "Se encontraron senales visuales sospechosas. Requiere revision manual.",
            )
        )
    elif visual != "consistent":
        messages.append(
            (
                "warning",
                "No hay evidencia suficiente sobre la apariencia del documento.",
            )
        )

    if not messages:
        messages.append(
            (
                "info",
                "Se detectaron firma y membrete, y la apariencia coincide con el "
                "tipo de documento. Esto no confirma que sea autentico.",
            )
        )
    return messages


def _show_result(result: dict[str, Any]) -> None:
    fields = result["fields"]
    document_type = _value(fields, "document_type")
    signature_type = _value(fields, "signature_type")
    letterhead = _value(fields, "letterhead_present")
    visual = _value(fields, "visual_consistency")

    st.subheader("Resultado")
    st.caption(f"Archivo analizado: {result['file']}")

    document_column, signature_column = st.columns(2)
    document_column.metric(
        "Tipo de documento",
        DOCUMENT_TYPES.get(document_type, document_type or "No identificado"),
    )
    signature_column.metric(
        "Firma",
        SIGNATURE_TYPES.get(signature_type, signature_type or "No identificada"),
    )

    letterhead_column, visual_column = st.columns(2)
    letterhead_column.metric(
        "Membrete",
        _boolean_result(letterhead),
        _value(fields, "letterhead_company") or None,
    )
    visual_column.metric(
        "Consistencia visual (no autenticidad)",
        VISUAL_RESULTS.get(visual, visual or "No evaluada"),
    )

    for level, message in _result_messages(
        document_type,
        signature_type,
        letterhead,
        visual,
    ):
        getattr(st, level)(message)

    findings = _value(fields, "visual_findings")
    if findings:
        st.write("**Hallazgos visuales**")
        st.write(findings)

    signature_evidence = _value(fields, "signature_evidence")
    if signature_evidence:
        st.write("**Evidencia de firma manuscrita**")
        st.write(signature_evidence)

    with st.expander("Ver resultado tecnico"):
        st.json(result)


def main() -> None:
    st.set_page_config(
        page_title="Validacion de documentos",
        page_icon="📄",
        layout="centered",
    )
    st.title("Validacion visual de documentos")
    st.write(
        "Carga un PDF para detectar firma manuscrita, membrete y consistencia "
        "visual con el tipo de documento."
    )
    endpoint = os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
    if not endpoint:
        st.error(
            "Falta CONTENTUNDERSTANDING_ENDPOINT. Configura la variable y reinicia "
            "la aplicacion."
        )
        st.stop()

    uploaded_file = st.file_uploader("Documento PDF", type=["pdf"])
    if uploaded_file is None:
        return

    st.caption(
        f"{uploaded_file.name} · {uploaded_file.size / 1024:.1f} KB"
    )
    if not st.button("Analizar documento", type="primary", use_container_width=True):
        return

    with tempfile.TemporaryDirectory() as temporary_directory:
        document_path = Path(temporary_directory) / Path(uploaded_file.name).name
        document_path.write_bytes(uploaded_file.getvalue())

        with st.spinner("Analizando el documento en Azure..."):
            try:
                result = validate_document(endpoint, document_path)
            except Exception as error:
                st.error("No se pudo analizar el documento.")
                st.exception(error)
                return

    st.session_state["last_result"] = result
    _show_result(result)


if __name__ == "__main__":
    main()
