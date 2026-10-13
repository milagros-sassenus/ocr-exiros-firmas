# Validacion visual de documentos con un LLM multimodal

La POC realiza tres controles:

1. presencia de una firma visible, manuscrita o electronica;
2. presencia de membrete de una compania o institucion;
3. consistencia visual con el tipo de documento.

El tercer control busca anomalias concretas: branding incorrecto, encabezados o
secciones ausentes, formato de identificadores invalido, estructura generica de
procesador de texto u otras diferencias respecto de documentos oficiales.

Una apariencia consistente no demuestra que un documento sea original. El
resultado `consistent` significa que no se encontraron anomalias visuales
concretas; `suspicious` e `inconclusive` requieren revision manual.

## Como funciona

1. Descarga los PDFs reales aprobados por el usuario desde un contenedor Blob
   privado.
2. Renderiza el documento objetivo en alta resolucion, sin ejecutar OCR local.
3. Envia las referencias aprobadas, el PDF objetivo y sus paginas a
   `your-multimodal-deployment`.
4. Structured Outputs devuelve:
   - `signature_present`;
   - `letterhead_present`;
   - `document_type`;
   - `visual_authenticity`;
   - `visual_findings`.

Cada referencia se etiqueta como `USER-APPROVED POSITIVE REFERENCE` y el
documento analizado como `TARGET DOCUMENT`. El modelo debe devolver
`inconclusive` cuando no exista una referencia relevante o no tenga evidencia
visual suficiente.

## Configuracion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
az login

export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="your-multimodal-deployment"
export APPROVED_REFERENCE_BLOB_CONTAINER_URL="https://your-storage-account.blob.core.windows.net/approved-document-references"
```

## Frontend

```bash
streamlit run app.py
```

Abrir `http://localhost:8501`, cargar un PDF y seleccionar **Analizar
documento**.

## Linea de comandos

```bash
python document_validation.py "/ruta/al/documento.pdf"
python document_validation.py "/ruta/al/documento.pdf" --output resultado.json
```

Salida:

```json
{
  "file": "ejemplo.pdf",
  "model_deployment": "your-multimodal-deployment",
  "reference_files": ["bank-certification-example-company.pdf"],
  "signature_present": true,
  "letterhead_present": true,
  "document_type": "constancia de inscripcion fiscal",
  "visual_authenticity": "consistent",
  "visual_findings": "Branding, estructura y formato de CUIT esperados."
}
```

## Pruebas

```bash
python -m unittest test_document_validation.py test_app.py
python samples/evaluate_samples.py --output evaluation.json
```

El conjunto sintetico contiene casos con firma manuscrita, firma electronica,
sin firma, sin membrete y con inconsistencias visuales deliberadas.
