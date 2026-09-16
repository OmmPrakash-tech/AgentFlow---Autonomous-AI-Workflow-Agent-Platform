package com.example.backend;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

// Persistence objects are deliberately package-private; controllers return explicit DTOs.
@Entity @Table(name="app_users")
class Account {
 @Id UUID id = UUID.randomUUID();
 @Column(nullable=false,unique=true,length=254) String email;
 @Column(nullable=false) String passwordHash;
 @Column(nullable=false) String role = "DEVELOPER";
 boolean enabled = true;
 boolean forceReset = false;
 int tokenVersion = 0;
 Instant createdAt = Instant.now();
}
@Entity @Table(name="projects")
class Project {
 @Id UUID id = UUID.randomUUID();
 @Column(nullable=false) UUID ownerId;
 @Column(nullable=false) String name;
 @Column(length=2000) String description;
 @Column(nullable=false) String workspacePath;
 String type = "LOCAL";
 Instant createdAt = Instant.now();
}
@Entity @Table(name="definitions",uniqueConstraints=@UniqueConstraint(columnNames={"kind","name"}))
class Definition {
 @Id UUID id = UUID.randomUUID();
 @Column(nullable=false) String kind;
 @Column(nullable=false) String name;
 UUID ownerId;
 @Column(columnDefinition="text",nullable=false) String configuration;
 boolean enabled = true;
 int revision = 1;
}
@Entity @Table(name="agent_runs")
class Run {
 @Id UUID id = UUID.randomUUID();
 @Column(nullable=false) UUID projectId;
 @Column(nullable=false) UUID ownerId;
 @Column(length=4000,nullable=false) String objective;
 String status = "QUEUED";
 String mode = "READ_ONLY";
 @Column(columnDefinition="text") String snapshot = "{}";
 Instant createdAt = Instant.now();
 Instant updatedAt = Instant.now();
 @Version long version;
}
@Entity @Table(name="audit_logs")
class Audit {
 @Id UUID id = UUID.randomUUID();
 UUID actorId;
 @Column(nullable=false) String action;
 String resource;
 @Column(length=2000) String detail;
 Instant createdAt = Instant.now();
}
@Entity @Table(name="reset_tokens")
class ResetToken {
 @Id String digest;
 @Column(nullable=false) UUID userId;
 Instant expiresAt;
 boolean used = false;
 @Version long version;
}
@Entity @Table(name="workspace_guard")
class WorkspaceGuard { @Id Integer id = 1; }
