FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ARG LEAN_VERSION=4.30.0
RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl zstd \
    && rm -rf /var/lib/apt/lists/* \
    && curl --fail --location --retry 3 \
       "https://github.com/leanprover/lean4/releases/download/v${LEAN_VERSION}/lean-${LEAN_VERSION}-linux.tar.zst" \
       --output /tmp/lean.tar.zst \
    && mkdir /opt/lean \
    && tar --extract --use-compress-program=unzstd \
       --file=/tmp/lean.tar.zst --directory=/opt/lean --strip-components=1 \
    && rm /tmp/lean.tar.zst

ENV PATH="/opt/lean/bin:${PATH}"
WORKDIR /workspace
COPY . .
RUN lake build
CMD ["lake", "build"]
