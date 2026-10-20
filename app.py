import os
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from document_validation import validate_document

VISUAL_RESULTS = {
    "consistent": "Consistente",
    "suspicious": "Sospechoso",
    "inconclusive": "No concluyente",
}


def _visual_message(status: str) -> tuple[str, str]:
    if status == "consistent":
        return (
            "info",
            "La apariencia es consistente con el tipo documental. Esto no "
            "demuestra autenticidad forense.",
        )
    if status == "suspicious":
        return (
            "error",
            "Se detectaron inconsistencias visuales. Requiere revision manual.",
        )
    return (
        "warning",
        "No hay evidencia visual suficiente. Requiere revision manual.",
    )


def _show_result(result: dict[str, Any]) -> None:
    st.subheader("Resultado")
    st.caption(f"Archivo analizado: {result['file']}")

    signature_column, letterhead_column = st.columns(2)
    signature_column.metric(
        "Firma",
        "Detectada" if result["signature_present"] else "No detectada",
    )
    letterhead_column.metric(
        "Membrete",
        "Detectado" if result["letterhead_present"] else "No detectado",
    )

    st.metric(
        "Apariencia del documento",
        VISUAL_RESULTS[result["visual_authenticity"]],
        result["document_type"],
    )

    if not result["signature_present"]:
        st.warning("No se detecto ninguna firma visible.")
    if not result["letterhead_present"]:
        st.warning("No se detecto membrete de una compania o institucion.")

    level, message = _visual_message(result["visual_authenticity"])
    getattr(st, level)(message)

    if result["visual_findings"]:
        st.write("**Hallazgos visuales**")
        st.write(result["visual_findings"])

    with st.expander("Ver resultado tecnico"):
        st.json(result)


def main() -> None:
    st.set_page_config(
        page_title="Validacion visual de documentos",
        page_icon="📄",
        layout="centered",
    )
    st.title("Validacion visual de documentos")
    st.write(
        "Carga un PDF para verificar firma, membrete y consistencia visual "
        "con el tipo de documento."
    )

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        st.error(
            "Falta AZURE_OPENAI_ENDPOINT. Configura la variable y reinicia "
            "la aplicacion."
        )
        st.stop()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not deployment or not deployment.strip():
        st.error(
            "Falta AZURE_OPENAI_DEPLOYMENT. Configura el deployment multimodal "
            "y reinicia la aplicacion."
        )
        st.stop()
    if not os.getenv("APPROVED_REFERENCE_BLOB_CONTAINER_URL"):
        st.error(
            "Falta APPROVED_REFERENCE_BLOB_CONTAINER_URL. Configura el "
            "contenedor aprobado y reinicia la aplicacion."
        )
        st.stop()

    uploaded_file = st.file_uploader("Documento PDF", type=["pdf"])
    if uploaded_file is None:
        return

    st.caption(f"{uploaded_file.name} · {uploaded_file.size / 1024:.1f} KB")
    if not st.button(
        "Analizar documento",
        type="primary",
        use_container_width=True,
    ):
        return

    with tempfile.TemporaryDirectory() as temporary_directory:
        document_path = Path(temporary_directory) / Path(uploaded_file.name).name
        document_path.write_bytes(uploaded_file.getvalue())

        with st.spinner("Analizando el documento con el modelo multimodal..."):
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
