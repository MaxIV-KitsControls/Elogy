FROM tiangolo/uwsgi-nginx-flask:flask-python3.5-index-upload

RUN apt update
RUN apt install -y libldap2-dev libsasl2-dev  # LDAP support

#RUN mkdir /app
RUN mkdir /app/elogy
COPY ./elogy/*.py /app/elogy/
RUN mkdir /app/elogy/api
COPY ./elogy/api/*.py /app/elogy/api/
#RUN mkdir /app/elogy/frontend
COPY ./elogy/frontend/build/* /app/static/
RUN mkdir /app/static/attachments
COPY ./run.py /app/main.py
COPY ./config.py /app
COPY ./requirements.txt /

COPY ./nginx.conf /etc/nginx/conf.d/

RUN pip3 install -r /requirements.txt
#RUN pip3 install uwsgi

#ENV HOME /app
#ENV LC_ALL C.UTF-8
#ENV LANG C.UTF-8
#WORKDIR /app
#ENV FLASK_APP elogy.app 

#EXPOSE 8000
ENV ELOGY_CONFIG_FILE /app/config.py
#ENTRYPOINT ["uwsgi", "--socket=0.0.0.0:8000", "--protocol=http",
#            "--file=run.py", "--processes=1", "--threads=5"]
