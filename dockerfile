FROM python:3.9

ARG APPDIR=/App

RUN useradd -m -d $APPDIR appuser
USER appuser
WORKDIR $APPDIR

COPY bot.py $APPDIR/
COPY botCommands $APPDIR/botcommands
COPY requirements.txt $APPDIR/

RUN cd $APPDIR \
    && pip install -r requirements.txt

ENTRYPOINT ["python", "bot.py"]
