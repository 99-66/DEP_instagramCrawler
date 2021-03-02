FROM python:3.6.6-slim

COPY ./ /instagram
WORKDIR /instagram

RUN apt-get update && apt install -y wget && wget http://172.16.0.60/repo/chrome/debian/google-chrome-stable_78.0.3904.97-1_amd64.deb
RUN apt --fix-broken install -y ./google-chrome-stable_78.0.3904.97-1_amd64.deb
RUN pip install -r requirements.txt

CMD ["/bin/sh"]