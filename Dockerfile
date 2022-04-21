FROM grobid/grobid
WORKDIR /opt/translate-source
COPY parse_func.py ./
COPY trans2PDF.py ./
COPY translate_func.py ./
COPY utils.py ./
CMD ["./trans2PDF.py", ""]
RUN python3 trans2PDF.py --