FROM apeworx/ape:0.8.4

USER 1000
WORKDIR /home/harambe/project

COPY requirements.txt .

RUN pip install -r requirements.txt && rm -f requirements.txt

