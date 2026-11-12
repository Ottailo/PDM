FROM python@sha256:1d6131b5d479888b43200645e03a78443c7157efbdb730e6b48129740727c312
COPY requirements.txt /build/requirements.txt
RUN python3 -I -m pip install --no-cache-dir --only-binary=:all: --no-deps --require-hashes -r /build/requirements.txt \
    && rm -rf /build /root/.cache
COPY parser.py /parser/parser.py
RUN chmod 0555 /parser /parser/parser.py
WORKDIR /parser
USER 65532:65532
ENTRYPOINT ["python3", "-I", "/parser/parser.py"]
CMD []
