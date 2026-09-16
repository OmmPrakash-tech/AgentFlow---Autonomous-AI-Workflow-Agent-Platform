package com.example.backend;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.domain.*;
import java.util.*;
interface Accounts extends JpaRepository<Account,UUID> { Optional<Account> findByEmail(String email); }
interface Projects extends JpaRepository<Project,UUID> { Page<Project> findByOwnerId(UUID id, Pageable pageable); }
interface Definitions extends JpaRepository<Definition,UUID> {
 List<Definition> findByKindOrderByName(String kind);
 Optional<Definition> findByKindAndName(String kind,String name);
}
interface Runs extends JpaRepository<Run,UUID> {
 Page<Run> findByOwnerId(UUID id, Pageable pageable);
 List<Run> findTop20ByStatusInOrderByUpdatedAtAsc(Collection<String> statuses);
 Page<Run> findByStatus(String status, Pageable pageable);
 Page<Run> findByOwnerIdAndStatus(UUID ownerId,String status,Pageable pageable);
}
interface Audits extends JpaRepository<Audit,UUID> {}
interface ResetTokens extends JpaRepository<ResetToken,String> {}
interface WorkspaceGuards extends JpaRepository<WorkspaceGuard,Integer> {
 @org.springframework.data.jpa.repository.Lock(jakarta.persistence.LockModeType.PESSIMISTIC_WRITE)
 @org.springframework.data.jpa.repository.Query("select g from WorkspaceGuard g where g.id=1")
 WorkspaceGuard lockRoot();
}
