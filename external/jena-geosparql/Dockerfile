FROM maven:3.9.11-eclipse-temurin-21@sha256:6fdc855a6ed81d288ca7ca37ac6ff5e9308b612485c0801d70b25a858c83d237 AS build
WORKDIR /build
COPY pom.xml ./
RUN mvn --batch-mode --quiet dependency:go-offline
COPY src ./src
RUN mvn --batch-mode --quiet -DskipTests package

FROM eclipse-temurin:21-jre@sha256:273396ed5998598ed1091e8d72711c2d36980a0e65103859c55a4e977a41ffd3
LABEL org.opencontainers.image.title="PULSE Apache Jena GeoSPARQL harness"
LABEL org.opencontainers.image.description="Pinned external GeoSPARQL comparison harness"
WORKDIR /opt/pulse
COPY --from=build /build/target/pulse-jena-geosparql-harness.jar ./harness.jar
USER 65532:65532
ENTRYPOINT ["java", "-jar", "/opt/pulse/harness.jar"]
