# BaseImage
FROM python:2.7
# Set ENV
ENV PYTHONUNBUFFERED 1
# Install NPM
RUN \
  cd /tmp && \
  wget http://nodejs.org/dist/node-latest.tar.gz && \
  tar xvzf node-latest.tar.gz && \
  rm -f node-latest.tar.gz && \
  cd node-v* && \
  ./configure && \
  CXX="g++ -Wno-unused-local-typedefs" make && \
  CXX="g++ -Wno-unused-local-typedefs" make install && \
  cd /tmp && \
  rm -rf /tmp/node-v* && \
  npm install -g npm && \
  echo -e '\n# Node.js\nexport PATH="node_modules/.bin:$PATH"' >> /root/.bashrc
# Get lessc
RUN npm install -g less
# Make our code folder
RUN mkdir /code
# Switch to our code folder
WORKDIR /code
# Install python requirements
ADD requirements.txt /code/
RUN pip install -r requirements.txt
# Add the data in /code to the root of the docker image
ADD . /code/
