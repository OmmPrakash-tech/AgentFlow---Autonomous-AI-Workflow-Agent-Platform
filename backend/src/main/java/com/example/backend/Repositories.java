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
 List<Run> findTop20ByStatusInOrderByCreatedAtAsc(Collection<String> statuses);
}
interface Audits extends JpaRepository<Audit,UUID> {}
interface ResetTokens extends JpaRepository<ResetToken,String> {}
