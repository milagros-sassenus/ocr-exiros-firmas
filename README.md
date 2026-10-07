# POC de validacion visual de documentos

POC corta para evaluar tres senales en documentos de proveedores:

1. presencia de firma holografica (manuscrita);
2. presencia de membrete;
3. consistencia visual con el tipo de documento declarado.

La solucion usa dos analizadores personalizados dentro del mismo recurso de
[Azure AI Content Understanding](https://learn.microsoft.com/azure/ai-services/content-understanding/document/overview).
El analizador documental resuelve tipo, membrete y consistencia. Para no perder
firmas escaneadas, cada pagina se renderiza localmente y un analizador visual
detecta las firmas. No se agrega otro servicio ni otro OCR.

## Alcance

`visual_consistency` es una senal para revision, no una certificacion forense de
que el archivo sea original. Un documento visualmente correcto puede estar
adulterado y uno legitimo puede tener baja calidad. Microsoft recomienda medir
el analizador con documentos reales y mantener revision humana:

- [Mejorar y evaluar analizadores](https://learn.microsoft.com/azure/ai-services/content-understanding/document/analyzer-improvement)
- [Transparency Note](https://learn.microsoft.com/azure/foundry/responsible-ai/content-understanding/transparency-note)

## Requisitos

- Python 3.10 o posterior.
- Un recurso Microsoft Foundry con Content Understanding.
- Modelos de completion y embeddings configurados como defaults.
- Una identidad con acceso al recurso. Para desarrollo local alcanza con
  `az login`.

No hace falta crear infraestructura para esta POC si ya existe un recurso
Foundry configurado.

## Como funciona

1. El PDF completo se envia al analizador documental de Content Understanding.
   Este identifica el tipo, el membrete y la consistencia visual.
2. Cada pagina se renderiza localmente como imagen a 2x.
3. Las imagenes se envian de a una al analizador visual para detectar firmas
   manuscritas pequenas o escaneadas.
4. La aplicacion combina ambos resultados y muestra las senales al usuario.

## Probar el frontend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:CONTENTUNDERSTANDING_ENDPOINT = "https://msassenus-1063-resource.cognitiveservices.azure.com/"
$env:CONTENTUNDERSTANDING_TRAINING_DATA_SAS_URL = "<URL SAS del contenedor>"
streamlit run app.py
```

Abrir `http://localhost:8501`, cargar un PDF y seleccionar **Analizar
documento**. La autenticacion local usa la sesion de `az login`.

## Probar por linea de comandos

```powershell
$env:CONTENTUNDERSTANDING_ENDPOINT = "https://msassenus-1063-resource.cognitiveservices.azure.com/"
python document_validation.py "C:\documentos\ejemplo.pdf"
```

La primera ejecucion crea `document_validation_poc_v4_official_reference` y
`signature_image_poc_v1`. Las siguientes los reutilizan.

El analizador documental usa in-context learning con el golden set de
`samples\official`. Para crearlo, el contenedor Blob debe incluir cada PDF y su
archivo homonimo `.labels.json`; la URL SAS necesita permisos Read y List. La
variable solo es necesaria para crear el analizador por primera vez. Nunca se
debe guardar una URL SAS en el repositorio.

Para guardar el resultado:

```powershell
python document_validation.py "C:\documentos\ejemplo.pdf" --output resultado.json
```

Opcionalmente se puede autenticar con una clave:

```powershell
$env:CONTENTUNDERSTANDING_KEY = "<clave>"
```

## Salida

La CLI devuelve los valores y, cuando el servicio los proporciona, confianza y
ubicacion de la evidencia:

```json
{
  "file": "ejemplo.pdf",
  "fields": {
    "handwritten_signature_present": {
      "value": true,
      "confidence": 0.91
    },
    "letterhead_present": {
      "value": true,
      "confidence": 0.95
    },
    "visual_consistency": {
      "value": "consistent"
    }
  }
}
```

En un flujo real, `suspicious`, `inconclusive` o resultados de baja confianza
deben derivarse a revision manual.

## Documentos sinteticos de prueba

Para generar seis documentos ficticios:

```powershell
.\.venv\Scripts\python.exe samples\generate_test_documents.py
```

Los PDF se crean en `samples\synthetic`. Todos incluyen una marca visible de
documento sintetico, usan empresas ficticias y datos sin validez.

El archivo `expected_results.json` contiene el resultado esperado para cada
caso:

1. banco completo, con membrete y firma;
2. banco con membrete pero sin firma;
3. carta firmada sin membrete;
4. supuesta constancia fiscal con apariencia generica;
5. certificado con marcas y emisor inconsistentes;
6. carta con firma electronica pero sin firma manuscrita.

Se pueden cargar de a uno desde el frontend. Las expectativas son hipotesis de
prueba: cualquier diferencia debe revisarse y puede servir para ajustar el
esquema o ampliar el conjunto de evaluacion.

## Fuentes oficiales para pruebas

El archivo `samples\official_sources.json` contiene una lista revisada de PDFs
publicos alojados en dominios oficiales de ARCA, AFIP, BCRA y Funcion Publica
de Colombia. Incluye la URL original, cantidad de paginas, objetivo de prueba y
hash SHA-256 observado durante la revision.

Para descargarlos localmente:

```powershell
.\.venv\Scripts\python.exe samples\download_official_samples.py
```

Los archivos se guardan en `samples\official` y estan excluidos de Git. El
descargador falla si una fuente deja de devolver un PDF o si su contenido
cambia respecto del documento revisado.

Conviene empezar por `afip-f460f.pdf`, que tiene cuatro paginas. Los documentos
largos generan una llamada visual por pagina y, por lo tanto, tardan y cuestan
mas. Estas fuentes sirven para probar apariencia y membrete; no deben tratarse
como casos falsificados ni como evidencia de fraude.

## Evaluar los analizadores

Los casos sinteticos y oficiales tienen resultados esperados para las senales
que se pueden etiquetar visualmente. Para ejecutar todos los casos y obtener
accuracy por campo:

```powershell
.\.venv\Scripts\python.exe samples\evaluate_samples.py --output evaluation.json
```

Se puede limitar la ejecucion con `--dataset synthetic` o
`--dataset official`. El comando devuelve codigo de salida 1 si algun caso no
coincide con su etiqueta.

Los documentos de `samples\official` forman el conjunto de referencia legitimo:
provienen de fuentes institucionales, su hash fue verificado y su apariencia,
membrete y formas de identificacion o firma se consideran validos. La
evaluacion oficial exige que se reconozcan como visualmente consistentes y no
los usa como ejemplos negativos de firma. Los casos sinteticos prueban por
separado la deteccion explicita de trazos manuscritos.
