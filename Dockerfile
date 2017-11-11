FROM python:3.6-alpine

RUN mkdir -p /usr/src/app /config/zones /config/logs
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip3 install --no-cache-dir -r requirements.txt

COPY cloudflare-ddns.py /usr/src/app
# COPY zones/* /config/zones/

VOLUME /config

ENTRYPOINT ["python", "cloudflare-ddns.py", "--docker", "--folder", "/config/zones"]
