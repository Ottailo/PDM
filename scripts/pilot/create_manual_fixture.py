"""Generate a clearly labeled synthetic PDF fixture outside customer storage.

It tests actual page extraction; it is not an OEM manual or engineering advice.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def create_pdf(destination: Path) -> None:
    content = (
        b'BT /F1 14 Tf 50 760 Td '
        b'(Machivital document-processing test fixture) Tj 0 -25 Td '
        b'(Synthetic test document - not an OEM manual.) Tj 0 -25 Td '
        b'(Procedure TEST-ONLY-42: verify this exact page text.) Tj 0 -25 Td '
        b'(Do not use this fixture to operate or repair equipment.) Tj ET'
    )
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream',
    ]
    document = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(document))
        document.extend(f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(document)
    document.extend(f'xref\n0 {len(offsets)}\n'.encode() + b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        document.extend(f'{offset:010d} 00000 n \n'.encode())
    document.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(document)


if __name__ == '__main__':
    from pypdf import PdfReader
    file = ROOT / '.pilot' / 'fixtures' / 'manual-test-only.pdf'
    create_pdf(file)
    reader = PdfReader(file)
    text = reader.pages[0].extract_text()
    assert len(reader.pages) == 1 and 'TEST-ONLY-42' in text
    print('PASS: synthetic PDF fixture has one extractable page and exact test marker')
