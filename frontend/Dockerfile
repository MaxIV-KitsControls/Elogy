FROM smebberson/alpine-nginx-nodejs

EXPOSE 80

RUN mkdir /elogy
WORKDIR /elogy

COPY package.json .
RUN npm i

COPY public public
COPY src src

RUN npm run build
RUN mv build/* /usr/html

COPY default.conf /etc/nginx/conf.d/default.conf