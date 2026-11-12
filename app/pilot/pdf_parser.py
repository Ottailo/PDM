"""Executed only as an isolated, bounded subprocess; never imports Flask."""
import json
import os
import sys


def limit_resources():
    if os.name=='posix':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(384*1024*1024,384*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(15,15))
        resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024*1024,2*1024*1024))
    elif os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Basic(ctypes.Structure):
            _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(name,ctypes.c_uint64) for name in ['ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
        class Extended(ctypes.Structure):
            _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p,wintypes.LPCWSTR]
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE,wintypes.HANDLE]
        job = kernel.CreateJobObjectW(None,None)
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x100 | 0x8  # Process memory and active process caps.
        info.BasicLimitInformation.ActiveProcessLimit = 1
        info.ProcessMemoryLimit = 384*1024*1024
        if not job or not kernel.SetInformationJobObject(job,9,ctypes.byref(info),ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(job,kernel.GetCurrentProcess()):
            raise RuntimeError('Unable to establish parser resource limits')


def main():
    limit_resources()
    from pypdf import PdfReader
    path,max_pages,max_text = sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
    reader = PdfReader(path,strict=True)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported')
    if not 1<=len(reader.pages)<=max_pages:
        raise ValueError('PDF exceeds the page limit')
    # Active content stays attachment-only, but reject it too: no JavaScript, launch or embedded files.
    dangerous = {'/JavaScript','/JS','/Launch','/EmbeddedFiles','/OpenAction','/AA','/RichMedia','/XFA','/SubmitForm','/ImportData'}
    from pypdf.generic import DictionaryObject,ArrayObject,IndirectObject
    visited = set()
    remaining = [reader.trailer]
    inspected = 0
    while remaining:
        obj = remaining.pop()
        if isinstance(obj,IndirectObject):
            identity = (obj.idnum,obj.generation)
            if identity in visited:
                continue
            visited.add(identity)
            obj = obj.get_object()
        inspected += 1
        if inspected>200000:
            raise ValueError('PDF object graph exceeds processing limits')
        if isinstance(obj,DictionaryObject):
            if dangerous.intersection(obj.keys()) or str(obj.get('/S','')) in dangerous:
                raise ValueError('PDF active content is not supported')
            remaining.extend(obj.values())
        elif isinstance(obj,ArrayObject):
            remaining.extend(obj)
    pages = []
    total = 0
    for page in reader.pages:
        value = page.extract_text() or ''
        total += len(value)
        if len(value)>100000 or total>max_text:
            raise ValueError('PDF extracted text exceeds processing limits')
        pages.append(value)
    print(json.dumps({'pages':pages},ensure_ascii=True))


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'error':str(error)[:200]}))
        sys.exit(1)
