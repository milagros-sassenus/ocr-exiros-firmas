# Arquitectura y ejecucion

## Arquitectura

1. `app.py` recibe un PDF desde Streamlit y lo guarda temporalmente.
2. `document_validation.py` envia el PDF completo al analyzer
   `document_validation_poc_v4_official_reference`, basado en
   `prebuilt-document`. Este detecta tipo, membrete, firma electronica y
   consistencia visual.
3. Cada pagina se convierte a PNG y se envia a `signature_image_poc_v1`,
   basado en `prebuilt-image`, para detectar firmas manuscritas.
4. Ambos resultados se combinan y se muestran en el frontend.

Los documentos de `samples/official` son el golden set legitimo. Estan
etiquetados y almacenados en el contenedor privado `official-reference` del
Storage Account `ocrexirosm1483pas`, dentro del resource group `ocr-exiros`.

## Como se forma el criterio

Cada referencia tiene dos archivos:

```text
documento.pdf
documento.pdf.labels.json
```

El PDF aporta la apariencia real: logo, estructura, tipografia y posiciones.
El `.labels.json` le indica a Azure que ese ejemplo tiene membrete y es
visualmente consistente.

Al crear el analyzer, Content Understanding usa el SAS para leer esos pares y
los incorpora como ejemplos de in-context learning. El criterio combina:

- el modelo base `prebuilt-document`;
- las definiciones de nuestros campos;
- los PDFs oficiales y sus etiquetas.

Luego, los documentos nuevos se envian directamente como bytes. Azure no
necesita consultar el contenedor en cada analisis; el SAS vuelve a ser
necesario solamente para crear o reconstruir el analyzer.

Los cuatro oficiales son referencias positivas. Todo archivo de
`samples/synthetic` tiene ground truth de documento falso y debe terminar en
revision, aunque algunas de sus senales visuales sean plausibles. El benchmark
compara tambien `review_required` para exponer falsos que todavia atraviesan el
filtro. Los sinteticos se usan para prueba, no como referencias positivas.

Se pueden sumar mas negativos fabricados o publicos, siempre separados del
entrenamiento y con procedencia, licencia y etiqueta revisadas. No conviene
usar archivos aleatorios de Internet sin verificar esos puntos.

Baseline actual del conjunto sintetico: 4 de 6 falsos terminan en revision.
Los casos 01 y 06 atraviesan el filtro porque tienen firma, membrete y
apariencia plausible. Son falsos negativos conocidos y demuestran que las
senales visuales solas no validan autenticidad.

`consistent` significa que el documento se parece visualmente a las referencias
legitimas. Un documento fabricado puede imitar esa apariencia, por lo que el
resultado no es una certificacion forense de autenticidad. La marca
`DOCUMENTO SINTETICO` identifica nuestros fixtures, pero no se usa como criterio
de deteccion porque un documento falso real no incluiria esa advertencia.

## Uso de SAS

El SAS permite que Content Understanding lea temporalmente los PDFs y labels
del golden set al crear o reconstruir el analyzer.

- Tipo: User Delegation SAS.
- Permisos usados: Read (`r`) y List (`l`).
- No se usa para los PDFs cargados por el usuario: esos se envian directamente
  como bytes.
- No hace falta para ejecutar normalmente porque el analyzer ya esta creado.
- Nunca debe guardarse en Git.

Variable utilizada durante una creacion o reconstruccion:

```powershell
$env:CONTENTUNDERSTANDING_TRAINING_DATA_SAS_URL = "<URL SAS del contenedor>"
```

## Como correrlo

```powershell
# 1. Entrar al proyecto
cd C:\Users\milly\GitHub\ocr-exiros-firmas

# 2. Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Autenticarse
az login

# 5. Configurar Azure
$env:CONTENTUNDERSTANDING_ENDPOINT = "https://msassenus-1063-resource.cognitiveservices.azure.com/"

# 6. Iniciar el frontend
streamlit run app.py
```

Abrir `http://localhost:8501`, cargar un PDF y presionar **Analizar documento**.

### Ejecutar por CLI

```powershell
python document_validation.py "C:\documentos\ejemplo.pdf"
```

### Ejecutar pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest test_document_validation.py
.\.venv\Scripts\python.exe samples\evaluate_samples.py --dataset all --output evaluation.json
```

## Microsoft Learn

- [Prebuilt analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers)
- [Custom analyzers e in-context learning](https://learn.microsoft.com/azure/ai-services/content-understanding/how-to/customize-analyzer-content-understanding-studio)
- [Mejora con ejemplos etiquetados](https://learn.microsoft.com/azure/ai-services/content-understanding/document/analyzer-improvement)
- [Referencia de knowledgeSources](https://learn.microsoft.com/rest/api/contentunderstanding/content-analyzers/create-or-replace?view=rest-contentunderstanding-2025-11-01)
- [User Delegation SAS](https://learn.microsoft.com/azure/storage/blobs/storage-blob-user-delegation-sas-create-cli)
- [DefaultAzureCredential y az login](https://learn.microsoft.com/azure/developer/python/sdk/authentication/local-development-dev-accounts)