FROM python:3.10.2-alpine

WORKDIR /app

# Start server command
CMD gunicorn app:app --worker-class eventlet --bind 0.0.0.0:8000 --workers 1 --log-level info --access-logfile -
EXPOSE 8000

# Convert pipenv to requirements.txt
RUN pip install pipenv
COPY Pipfile* /tmp/
RUN cd /tmp && pipenv lock --requirements > /app/requirements.txt

# Install dependencies
RUN apk add --no-cache --virtual .build-deps \
  build-base postgresql-dev libffi-dev \
  && pip install -r requirements.txt \
  && find /usr/local \
  \( -type d -a -name test -o -name tests \) \
  -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
  -exec rm -rf '{}' + \
  && runDeps="$( \
  scanelf --needed --nobanner --recursive /usr/local \
  | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
  | sort -u \
  | xargs -r apk info --installed \
  | sort -u \
  )" \
  && apk add --virtual .rundeps $runDeps \
  && apk del .build-deps

# Copy source code to container
COPY . /app
