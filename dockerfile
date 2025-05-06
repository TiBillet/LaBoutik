FROM python:3.8-bullseye

## UPDATE
RUN apt-get update && apt-get upgrade -y

## POSTGRES CLIENT
RUN mkdir -p /usr/share/man/man1
RUN mkdir -p /usr/share/man/man7
RUN apt-get install -y --no-install-recommends postgresql-client

RUN apt-get install -y nano iputils-ping curl borgbackup cron gettext supervisor

RUN useradd -ms /bin/bash tibillet

# Cron for Dump and Backup task
RUN chmod u+s /usr/sbin/cron
COPY ./cron/cron_task /etc/cron.d/cron_task
RUN chmod 0644 /etc/cron.d/cron_task
RUN crontab -u tibillet /etc/cron.d/cron_task

USER tibillet

## PYTHON
ENV POETRY_NO_INTERACTION=1
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.4 python3 -
ENV PATH="/home/tibillet/.local/bin:$PATH"

COPY --chown=tibillet:tibillet ./ /DjangoFiles
COPY --chown=tibillet:tibillet ./bashrc /home/tibillet/.bashrc

WORKDIR /DjangoFiles
RUN poetry install

CMD ["bash", "start_services.sh"]
