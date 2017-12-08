# Nginx on Debian 9 (Stretch)

This image provides a basic nginx hosting environment. The intent is for the web content itself to be stored in persistent storage wihch is then mounted in to this image at `/var/www`

## Updates

Please consult https://wiki.debian.org/LTS for information regarding debian 9 lifecycle.

## Usage

Please note this image is explictly intended to be run as a non-privileged user. Ensure you specify a user id (UID) other than zero when you run it. Running as root will not function.


```bash
UID=999
PORT=80
WEB_ROOT="/var/www/"

docker run -u ${UID}:0 -p ${PORT}:8080 -v ${WEB_ROOT}:/var/www/ 1and1internet/debian-9-nginx
```

## Building and testing

A simple Makefile is included for your convience. It assumes a linux environment with a docker socket available at `/var/run/docker.sock`

To build and test just run `make`.
You can also just `make pull`, `make build` and `make test` separately.

Please see the top of the Makefile for various variables which you may choose to customise. Variables may be passed as arguments, e.g. `make IMAGE_NAME=bob` or `make build BUILD_ARGS="--rm --no-cache"`

## Modifying the tests

All tests are run using the tespack-framework image. See 1and1internet/testpack-framework for more information
