FROM python:3.6-alpine

# add necessary folders
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# install all python modules
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# copy the python script
COPY cloudflare-ddns.py .

# mount necessary folders
VOLUME /config/zones
VOLUME /config/logs

ENTRYPOINT ["python", "cloudflare-ddns.py", "--docker", "--daemon", "--folder", "/config/zones"]
