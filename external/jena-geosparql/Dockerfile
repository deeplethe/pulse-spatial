FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml ./
RUN mvn --batch-mode --quiet dependency:go-offline
COPY src ./src
RUN mvn --batch-mode --quiet -DskipTests package

FROM eclipse-temurin:21-jre
LABEL org.opencontainers.image.title="PULSE Apache Jena GeoSPARQL harness"
LABEL org.opencontainers.image.description="Pinned external GeoSPARQL comparison harness"
WORKDIR /opt/pulse
COPY --from=build /build/target/pulse-jena-geosparql-harness.jar ./harness.jar
USER 65532:65532
ENTRYPOINT ["java", "-jar", "/opt/pulse/harness.jar"]
