FROM python:3.8-bullseye

## UPDATE
RUN apt-get update && apt-get upgrade -y

## POSTGRES CLIENT
RUN mkdir -p /usr/share/man/man1
RUN mkdir -p /usr/share/man/man7
RUN apt-get install -y --no-install-recommends postgresql-client

RUN apt-get install -y nano iputils-ping curl borgbackup cron gettext


RUN useradd -ms /bin/bash tibillet
USER tibillet

ENV POETRY_NO_INTERACTION=1

## PYTHON
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/home/tibillet/.local/bin:$PATH"

COPY --chown=tibillet:tibillet ./ /DjangoFiles
COPY --chown=tibillet:tibillet ./bashrc /home/tibillet/.bashrc
COPY --chown=tibillet:tibillet ./cron /cron

WORKDIR /DjangoFiles
RUN poetry install

CMD ["bash", "start.sh"]



# Before build : collectstatic
# docker build -t tibillet/laboutik:beta4 .
# docker push tibillet/laboutik:beta4 .
