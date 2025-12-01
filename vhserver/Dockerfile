FROM debian:stable-slim

RUN apt-get update && apt-get install -y \
    usbutils wget && \
    rm -rf /var/lib/apt/lists/*

# Download ARM64 VirtualHere USB Server binary
RUN wget https://virtualhere.com/sites/default/files/usbserver/vhusbdarm64 -O /usr/local/bin/vhusbd && \
    chmod +x /usr/local/bin/vhusbd

EXPOSE 7575

COPY run_vhusbd.sh /usr/local/bin/run_vhusbd.sh
CMD ["/usr/local/bin/run_vhusbd.sh"]
