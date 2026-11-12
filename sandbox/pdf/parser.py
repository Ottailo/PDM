"""Parser-only entrypoint. No application imports, credentials, or network code.

Extraction and active-content policy are transplanted from app/pilot/pdf_parser.py.
The host enforces OS containment and independently validates the JSON response.
"""
import json
import logging
import os
import sys
import tempfile

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200
MAX_TEXT = 1000000


class Rejected(ValueError):
    pass


def limits(argv):
    if len(argv) != 3 or any(not value.isascii() or not value.isdecimal() for value in argv):
        raise Rejected('Invalid parser limits')
    values = tuple(map(int, argv))
    if any(not 1 <= value <= ceiling for value, ceiling in zip(values, (MAX_BYTES, MAX_PAGES, MAX_TEXT))):
        raise Rejected('Invalid parser limits')
    return values


def resource_limits(max_bytes):
    if os.name == 'posix':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_bytes,) * 2)
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def extract(stream, max_bytes, max_pages, max_text):
    from pypdf import PdfReader
    from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject
    with tempfile.TemporaryFile(mode='w+b') as file:
        total = 0
        while True:
            chunk = stream.read(min(65536, max_bytes + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise Rejected('PDF exceeds the byte limit')
            file.write(chunk)
        if not total:
            raise Rejected('Empty PDF')
        file.seek(0)
        if not file.read(5) == b'%PDF-':
            raise Rejected('Invalid PDF signature')
        file.seek(0)
        reader = PdfReader(file, strict=True)
        if reader.is_encrypted:
            raise Rejected('Encrypted PDFs are not supported')
        if not 1 <= len(reader.pages) <= max_pages:
            raise Rejected('PDF exceeds the page limit')
        dangerous = {'/JavaScript', '/JS', '/Launch', '/EmbeddedFiles', '/OpenAction', '/AA', '/RichMedia', '/XFA', '/SubmitForm', '/ImportData'}
        visited = set()
        remaining = [reader.trailer]
        inspected = 0
        while remaining:
            obj = remaining.pop()
            if isinstance(obj, IndirectObject):
                identity = (obj.idnum, obj.generation)
                if identity in visited:
                    continue
                visited.add(identity)
                obj = obj.get_object()
            inspected += 1
            if inspected > 200000 or len(remaining) > 200000:
                raise Rejected('PDF object graph exceeds processing limits')
            if isinstance(obj, DictionaryObject):
                if dangerous.intersection(obj.keys()) or str(obj.get('/S', '')) in dangerous:
                    raise Rejected('PDF active content is not supported')
                remaining.extend(obj.values())
            elif isinstance(obj, ArrayObject):
                remaining.extend(obj)
        pages = []
        total = 0
        for page in reader.pages:
            value = page.extract_text() or ''
            total += len(value)
            if len(value) > 100000 or total > max_text:
                raise Rejected('PDF extracted text exceeds processing limits')
            pages.append(value)
        return pages


def main():
    logging.disable(logging.CRITICAL)
    max_bytes, max_pages, max_text = limits(sys.argv[1:])
    resource_limits(max_bytes)
    pages = extract(sys.stdin.buffer, max_bytes, max_pages, max_text)
    output = json.dumps({'pages': pages}, ensure_ascii=True, separators=(',', ':'))
    if len(output) > max_text * 6 + max_pages * 4 + 100:
        raise Rejected('Parser output exceeds limits')
    print(output)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never echo untrusted parser exception strings or document contents.
        message = str(error) if isinstance(error, Rejected) else 'PDF could not be parsed safely'
        print(json.dumps({'error': message[:200]}))
        sys.exit(1)
