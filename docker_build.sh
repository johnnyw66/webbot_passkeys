chmod +x *.sh

# Capture all arguments
ARGS="$@"

# Run docker build with the Dockerfile.freeze and any args passed
docker build $ARGS -f Dockerfile.freeze -t webbot .

