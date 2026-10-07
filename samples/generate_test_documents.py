import json
from pathlib import Path

import pymupdf

SAMPLES_DIRECTORY = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = SAMPLES_DIRECTORY / "synthetic"
PAGE_WIDTH = 595
PAGE_HEIGHT = 842


def _new_document(title: str) -> tuple[pymupdf.Document, pymupdf.Page]:
    document = pymupdf.open()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text(
        (155, 420),
        "DOCUMENTO SINTETICO - SOLO PRUEBAS",
        fontsize=26,
        color=(0.9, 0.9, 0.9),
        rotate=90,
    )
    page.insert_text((50, 810), title, fontsize=7, color=(0.55, 0.55, 0.55))
    return document, page


def _letterhead(
    page: pymupdf.Page,
    company: str,
    subtitle: str,
    color: tuple[float, float, float],
) -> None:
    page.draw_rect((45, 42, 95, 92), color=color, fill=color)
    page.draw_circle((70, 67), 13, color=(1, 1, 1), width=3)
    page.insert_text((110, 63), company, fontsize=18, color=color)
    page.insert_text((110, 82), subtitle, fontsize=9, color=(0.25, 0.25, 0.25))
    page.draw_line((45, 105), (550, 105), color=color, width=1.5)


def _footer(page: pymupdf.Page, company: str) -> None:
    page.draw_line((45, 770), (550, 770), color=(0.75, 0.75, 0.75))
    page.insert_text(
        (45, 790),
        f"{company} | Datos y entidades completamente ficticios",
        fontsize=7,
        color=(0.4, 0.4, 0.4),
    )


def _signature(page: pymupdf.Page, x: float, y: float) -> None:
    shape = page.new_shape()
    shape.draw_bezier(
        (x, y),
        (x + 18, y - 35),
        (x + 20, y + 25),
        (x + 45, y - 8),
    )
    shape.draw_bezier(
        (x + 30, y),
        (x + 55, y - 32),
        (x + 58, y + 15),
        (x + 95, y - 10),
    )
    shape.draw_line((x - 8, y + 8), (x + 112, y + 4))
    shape.finish(color=(0.1, 0.15, 0.35), width=1.6)
    shape.commit()


def _body(page: pymupdf.Page, heading: str, paragraphs: list[str]) -> None:
    page.insert_textbox(
        (55, 135, 540, 180),
        heading,
        fontsize=14,
        fontname="hebo",
        align=pymupdf.TEXT_ALIGN_CENTER,
    )
    y = 205
    for paragraph in paragraphs:
        used = page.insert_textbox(
            (65, y, 530, y + 90),
            paragraph,
            fontsize=10,
            lineheight=1.35,
            align=pymupdf.TEXT_ALIGN_JUSTIFY,
        )
        y += max(55, 90 - used) + 15


def _save(document: pymupdf.Document, filename: str) -> None:
    destination = OUTPUT_DIRECTORY / filename
    document.set_metadata(
        {
            "title": filename,
            "author": "POC ocr-exiros-firmas",
            "subject": "Documento sintetico para pruebas",
        }
    )
    document.save(destination)
    document.close()


def create_bank_certificate_complete() -> None:
    document, page = _new_document("Caso 01: banco, membrete y firma manuscrita")
    _letterhead(page, "BANCO RIO CLARO", "Banca empresas", (0.08, 0.25, 0.52))
    _body(
        page,
        "CERTIFICACION BANCARIA",
        [
            "Banco Rio Claro S.A. certifica que LOGISTICA HORIZONTE DEMO S.A.S., "
            "identificada con CUIT de prueba 00-00000000-0, mantiene una cuenta "
            "corriente activa en nuestra entidad.",
            "Cuenta de prueba: 000-000000/0. CBU de prueba: "
            "0000000000000000000000. Esta informacion carece de validez comercial.",
            "Se expide exclusivamente para probar un sistema automatico.",
        ],
    )
    page.insert_text((65, 610), "Atentamente,", fontsize=10)
    page.insert_text((65, 635), "Firma:", fontsize=9)
    _signature(page, 75, 665)
    page.insert_text((65, 700), "ANA PRUEBA", fontsize=9)
    page.insert_text((65, 715), "Gerente de cuentas - personaje ficticio", fontsize=8)
    _footer(page, "Banco Rio Claro S.A.")
    _save(document, "01_banco_completo_firma_membrete.pdf")


def create_bank_certificate_without_signature() -> None:
    document, page = _new_document("Caso 02: banco y membrete, sin firma")
    _letterhead(page, "BANCO RIO CLARO", "Banca empresas", (0.08, 0.25, 0.52))
    _body(
        page,
        "CERTIFICACION BANCARIA",
        [
            "Banco Rio Claro S.A. certifica que LOGISTICA HORIZONTE DEMO S.A.S. "
            "mantiene una cuenta de prueba en nuestra entidad.",
            "CUIT de prueba: 00-00000000-0. Cuenta: 000-000000/0.",
            "Documento generado sin firma para evaluar el detector.",
        ],
    )
    page.insert_text((65, 620), "Atentamente,", fontsize=10)
    page.insert_text((65, 675), "Firma: ______________________________", fontsize=9)
    _footer(page, "Banco Rio Claro S.A.")
    _save(document, "02_banco_sin_firma.pdf")


def create_letter_without_letterhead() -> None:
    document, page = _new_document("Caso 03: firma manuscrita, sin membrete")
    _body(
        page,
        "DECLARACION DE CUMPLIMIENTO",
        [
            "LOGISTICA HORIZONTE DEMO S.A.S. declara que los fondos utilizados "
            "en su actividad provienen de operaciones licitas.",
            "La sociedad manifiesta conocer las politicas aplicables de prevencion "
            "y control. Todos los nombres y datos de este archivo son ficticios.",
        ],
    )
    page.insert_text((65, 570), "Firma del representante:", fontsize=10)
    _signature(page, 80, 630)
    page.insert_text((65, 675), "PEDRO EJEMPLO - personaje ficticio", fontsize=8)
    _save(document, "03_carta_firmada_sin_membrete.pdf")


def create_plain_tax_claim() -> None:
    document, page = _new_document("Caso 04: supuesto fiscal con apariencia pobre")
    page.insert_text((65, 105), "AGENCIA FISCAL DEMO", fontsize=12)
    page.insert_text((65, 155), "CONSTANCIA DE INSCRIPCION FISCAL", fontsize=16)
    page.insert_textbox(
        (65, 210, 525, 390),
        "CUIT: 00-00000000-0\n"
        "Razon social: LOGISTICA HORIZONTE DEMO S.A.S.\n"
        "Estado: ACTIVO\n\n"
        "Este texto fue escrito deliberadamente con una apariencia generica, "
        "sin estructura institucional, codigo de verificacion ni elementos "
        "graficos esperables. Solo sirve para probar la clasificacion visual.",
        fontsize=11,
        lineheight=1.3,
    )
    _save(document, "04_constancia_fiscal_word_sospechosa.pdf")


def create_mismatched_brands() -> None:
    document, page = _new_document("Caso 05: marcas e identidad inconsistentes")
    _letterhead(page, "BANCO RIO CLARO", "Banca empresas", (0.08, 0.25, 0.52))
    _body(
        page,
        "CERTIFICACION BANCARIA",
        [
            "COOPERATIVA MONTE AZUL certifica que INDUSTRIAS DEL SOL DEMO S.A. "
            "mantiene una cuenta activa.",
            "El encabezado, el emisor del cuerpo y el firmante pertenecen "
            "deliberadamente a entidades ficticias diferentes.",
        ],
    )
    page.insert_text((65, 585), "Firma del responsable:", fontsize=9)
    _signature(page, 80, 620)
    page.insert_text((65, 665), "MARTA EJEMPLO", fontsize=9)
    page.insert_text((65, 680), "Financiera Laguna Verde", fontsize=9)
    _footer(page, "Banco Rio Claro S.A.")
    _save(document, "05_banco_marcas_inconsistentes.pdf")


def create_electronic_signature_only() -> None:
    document, page = _new_document("Caso 06: firma electronica, sin manuscrita")
    _letterhead(page, "TENARIS DEMO", "Programa de proveedores", (0.3, 0.3, 0.3))
    _body(
        page,
        "CARTA DE CUMPLIMIENTO",
        [
            "La empresa ficticia declara conocer las normas aplicables a su "
            "actividad y certifica la informacion incluida en este documento.",
            "No existe una firma manuscrita en esta pagina.",
        ],
    )
    page.draw_rect(
        (65, 560, 530, 690),
        color=(0.15, 0.25, 0.42),
        fill=(0.94, 0.96, 0.99),
        width=1,
    )
    page.insert_text((85, 590), "FIRMADO ELECTRONICAMENTE", fontsize=12)
    page.insert_text((85, 620), "Firmante: USUARIO DEMO", fontsize=9)
    page.insert_text((85, 640), "Documento ID: TEST-0000-NO-VALIDO", fontsize=9)
    page.insert_text((85, 660), "Verificacion: CODIGO-DE-PRUEBA", fontsize=9)
    _footer(page, "Tenaris Demo")
    _save(document, "06_carta_solo_firma_electronica.pdf")


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    create_bank_certificate_complete()
    create_bank_certificate_without_signature()
    create_letter_without_letterhead()
    create_plain_tax_claim()
    create_mismatched_brands()
    create_electronic_signature_only()

    expectations = {
        "01_banco_completo_firma_membrete.pdf": {
            "handwritten_signature_present": True,
            "letterhead_present": True,
            "visual_consistency": "consistent",
            "review_required": True,
        },
        "02_banco_sin_firma.pdf": {
            "handwritten_signature_present": False,
            "letterhead_present": True,
            "visual_consistency": "consistent",
            "review_required": True,
        },
        "03_carta_firmada_sin_membrete.pdf": {
            "handwritten_signature_present": True,
            "letterhead_present": False,
            "visual_consistency": "consistent",
            "review_required": True,
        },
        "04_constancia_fiscal_word_sospechosa.pdf": {
            "handwritten_signature_present": False,
            "letterhead_present": False,
            "visual_consistency": "suspicious",
            "review_required": True,
        },
        "05_banco_marcas_inconsistentes.pdf": {
            "handwritten_signature_present": True,
            "letterhead_present": True,
            "visual_consistency": "suspicious",
            "review_required": True,
        },
        "06_carta_solo_firma_electronica.pdf": {
            "handwritten_signature_present": False,
            "letterhead_present": True,
            "signature_type": "electronic",
            "visual_consistency": "consistent",
            "review_required": True,
        },
    }
    (OUTPUT_DIRECTORY / "expected_results.json").write_text(
        json.dumps(expectations, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created {len(expectations)} documents in {OUTPUT_DIRECTORY.resolve()}")


if __name__ == "__main__":
    main()
