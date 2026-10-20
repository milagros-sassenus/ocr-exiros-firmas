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
3. Envia las referencias aprobadas, el PDF objetivo y sus paginas al deployment
   multimodal de Azure OpenAI configurado por el usuario.
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

En Windows con Git Bash o MSYS2/UCRT64:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Si `.venv` ya existe, omitir su creacion y ejecutar solo la activacion
correspondiente al sistema operativo.

Con el entorno activado:

```bash
python -m pip install -r requirements.txt
az login

export AZURE_OPENAI_ENDPOINT="https://<tu-recurso>.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="<tu-deployment-multimodal>"
export APPROVED_REFERENCE_BLOB_CONTAINER_URL="https://<tu-cuenta>.blob.core.windows.net/<tu-contenedor>"
```

Reemplazar los valores de ejemplo por recursos propios. Las tres variables son
obligatorias. El deployment debe admitir PDFs, imagenes y Structured Outputs.
La autenticacion usa `DefaultAzureCredential` (por ejemplo, `az login`); para
Azure OpenAI tambien se puede configurar `AZURE_OPENAI_API_KEY` en el entorno.
El acceso al contenedor privado siempre usa `DefaultAzureCredential`.

No guardar claves, tokens, URLs con SAS ni documentos reales en el repositorio.
Los archivos `.env` y la configuracion local de Streamlit se excluyen de Git;
la aplicacion no carga archivos `.env` automaticamente.

Si guardas tu configuracion en `.env.local`, cargarla en Git Bash o MSYS2/UCRT64
antes de iniciar la aplicacion:

```bash
set -a
source .env.local
set +a
```

## Frontend

```bash
python -m streamlit run app.py
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
  "model_deployment": "mi-deployment-multimodal",
  "reference_files": ["referencia-bancaria-ejemplo.pdf"],
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

## Antes de publicar

Revisar tambien el historial de Git: reemplazar datos en la version actual no
los elimina de commits anteriores. Si hubo credenciales expuestas, revocarlas o
rotarlas; borrar el historial no invalida una credencial.
No publicar PDFs reales ni resultados de analisis con datos personales.
