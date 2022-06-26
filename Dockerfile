FROM ghcr.io/opsdroid/opsdroid:latest

USER root
RUN apk update && apk add --no-cache ffmpeg opus-dev gcc
# gcc needed on alpine due to
# https://github.com/python/cpython/issues/65821
# https://github.com/docker-library/python/issues/111
RUN pip install humanize
RUN pip install pymumble
USER opsdroid
