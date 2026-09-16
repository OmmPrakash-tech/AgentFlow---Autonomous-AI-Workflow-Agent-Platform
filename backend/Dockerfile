FROM maven:3-eclipse-temurin-25 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q dependency:go-offline
COPY src src
RUN mvn -q -DskipTests package
FROM eclipse-temurin:25-jre
WORKDIR /app
RUN groupadd --gid 10001 agentflow && useradd --uid 10001 --gid 10001 --no-create-home agentflow
COPY --from=build /src/target/backend-0.1.0.jar app.jar
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["java","-XX:MaxRAMPercentage=70","-jar","app.jar"]
