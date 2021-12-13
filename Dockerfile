FROM python:3.9.9-slim-buster

# Run as non-root
ENV USER checkov
ENV UID 10001
ENV GROUP checkov
ENV GID 10001
ENV HOME /home/$USER
RUN addgroup --gid $GID $GROUP
RUN adduser --uid $UID --gid $GID $USER

# Python code
COPY . $HOME/
RUN chown -R $USER:$GROUP $HOME
RUN chmod +x $HOME/checkov.sh

# Install requirements
RUN pip install --no-cache-dir -r $HOME/requirements.txt

USER $UID:$GID
WORKDIR $HOME
CMD ["./checkov.sh"]