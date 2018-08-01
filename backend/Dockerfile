FROM tiangolo/uwsgi-nginx:python3.6

RUN apt-get update && \
	apt-get install -y \
	libldap2-dev \
	libsasl2-dev

RUN mkdir /app/elogy

WORKDIR /app/elogy

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir /var/elogy
RUN mkdir /var/elogy/db
RUN mkdir /var/elogy/attachments

EXPOSE 80

ENTRYPOINT ["uwsgi", "--socket=0.0.0.0:80", "--protocol=http", "--file=run.py", "--callable=app"]
