package com.example.backend;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;

@RestController @RequestMapping("/api")
class PlatformController {
 record ProjectInput(@NotBlank @Size(max=120) String name,@Size(max=2000) String description,@NotBlank @Size(max=200) String workspacePath) {}
 record DefinitionInput(@NotBlank @Size(max=120) String name,@NotNull Map<String,Object> configuration,boolean enabled) {}
 record UserUpdate(@Pattern(regexp="ADMIN|DEVELOPER|ANALYST|VIEWER") @NotNull String role,boolean enabled,boolean forceReset) {}
 final Access access; final Projects projects; final Definitions definitions; final Accounts accounts; final Audits audits; final ResetTokens resets; final ObjectMapper json;
 final Path root;
 final WorkspaceGuards guards;
 PlatformController(Access access,Projects p,Definitions d,Accounts a,Audits audits,ResetTokens resets,ObjectMapper json,WorkspaceGuards guards,@Value("${agentflow.workspace-root}") String root) {
  this.access=access; projects=p; definitions=d; accounts=a; this.audits=audits; this.resets=resets; this.json=json; this.guards=guards; this.root=Path.of(root).toAbsolutePath().normalize();
 }
 static Pageable page(int page) { return PageRequest.of(Math.max(0,page),25,Sort.by("createdAt").descending()); }
 Map<String,Object> project(Project p) { return Map.of("id",p.id,"name",p.name,"description",p.description==null?"":p.description,"workspacePath",p.workspacePath,"type",p.type,"createdAt",p.createdAt); }
 @GetMapping("/projects") Object projects(Authentication auth,@RequestParam(defaultValue="0") int page) {
  var a=access.user(auth); access.require(a,"READ");
  return (a.role.equals("ADMIN")?projects.findAll(page(page)):projects.findByOwnerId(a.id,page(page))).map(this::project);
 }
 @PostMapping("/projects") @Transactional
 Object createProject(Authentication auth,@Valid @RequestBody ProjectInput input) throws Exception {
  var a=access.user(auth); access.require(a,"WRITE");
  Path relative=Path.of(input.workspacePath());
  if(relative.isAbsolute()||relative.toString().contains(":")) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"Use a relative workspace path");
  Path realRoot=root.toRealPath(); Path resolved=realRoot.resolve(relative).toRealPath();
  if(!resolved.startsWith(realRoot)||resolved.equals(realRoot)||!Files.isDirectory(resolved)) throw Access.denied();
  if(guards.lockRoot()==null) throw new IllegalStateException("Workspace lock not initialized");
  for(var existing:projects.findAll()) {
   Path reserved=realRoot.resolve(existing.workspacePath).normalize();
   if(resolved.startsWith(reserved)||reserved.startsWith(resolved)) throw new ResponseStatusException(HttpStatus.CONFLICT,"Workspace overlaps a registered project");
  }
  var p=new Project(); p.name=input.name(); p.description=input.description(); p.workspacePath=realRoot.relativize(resolved).toString().replace('\\','/'); p.ownerId=a.id;
  projects.save(p); access.audit(a,"PROJECT_CREATED",p.id,"Approved workspace registered"); return project(p);
 }
 Map<String,Object> definition(Definition d) { return Map.of("id",d.id,"name",d.name,"configuration",json.readValue(d.configuration,Map.class),"enabled",d.enabled,"revision",d.revision); }
 String kind(String path) { return switch(path) { case "agents"->"AGENT"; case "tools"->"TOOL"; case "workflows"->"WORKFLOW"; default->throw new ResponseStatusException(HttpStatus.NOT_FOUND); }; }
 @GetMapping("/{registry:agents|tools|workflows}") Object definitions(Authentication auth,@PathVariable String registry) {
  var a=access.user(auth); access.require(a,"READ"); return definitions.findByKindOrderByName(kind(registry)).stream().filter(d->d.ownerId==null||a.role.equals("ADMIN")||a.id.equals(d.ownerId)).map(this::definition).toList();
 }
 @PostMapping("/{registry:agents|tools|workflows}") @Transactional
 Object saveDefinition(Authentication auth,@PathVariable String registry,@Valid @RequestBody DefinitionInput input) {
  var a=access.user(auth); access.require(a,registry.equals("workflows")?"WRITE":"ADMIN");
  if(json.writeValueAsString(input.configuration()).length()>32000) throw new IllegalArgumentException();
  var d=definitions.findByKindAndName(kind(registry),input.name()).orElseGet(Definition::new);
  if(d.name!=null) { if(d.ownerId==null) access.require(a,"ADMIN"); else access.owns(a,d.ownerId); }
  else if(registry.equals("workflows")) d.ownerId=a.id;
  if(registry.equals("workflows")) {
   Object nodes=input.configuration().get("agents");
   if(!(nodes instanceof List<?> agents)||agents.isEmpty()||agents.size()>12) throw new IllegalArgumentException();
   for(Object node:agents) if(!(node instanceof String name)||definitions.findByKindAndName("AGENT",name).filter(x->x.enabled).isEmpty()) throw new IllegalArgumentException();
  }
  if(registry.equals("agents")) {
   Object allowed=input.configuration().get("available_tools");
   if(!(allowed instanceof List<?> tools)||tools.size()>9) throw new IllegalArgumentException();
   for(Object tool:tools) if(!(tool instanceof String name)||definitions.findByKindAndName("TOOL",name).isEmpty()) throw new IllegalArgumentException();
   Object iterations=input.configuration().getOrDefault("max_iterations",4);
   if(!(iterations instanceof Number n)||n.intValue()<1||n.intValue()>4) throw new IllegalArgumentException();
   if(!"qwen3:8b".equals(input.configuration().getOrDefault("model","qwen3:8b"))) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"This deployment uses qwen3:8b");
  }
  if(registry.equals("tools")) {
   if(d.name==null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"Tools must be implemented in the engine before registration");
   String enforcedRisk=input.name().equals("modify_file")?"MEDIUM":input.name().equals("run_tests")?"HIGH":"LOW";
   if(!enforcedRisk.equals(input.configuration().get("risk_level"))) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"Tool risk is enforced by engine policy");
  }
  if(d.id!=null && d.name!=null) d.revision++;
  d.kind=kind(registry); d.name=input.name(); d.configuration=json.writeValueAsString(input.configuration()); d.enabled=input.enabled();
  definitions.save(d); access.audit(a,"REGISTRY_UPDATED",d.id,d.kind+" "+d.name); return definition(d);
 }
 @GetMapping("/audit") Object audit(Authentication auth,@RequestParam(defaultValue="0") int page) {
  var a=access.user(auth); access.require(a,"ADMIN");
  return audits.findAll(page(page)).map(x->Map.of("id",x.id,"action",x.action,"resource",x.resource,"detail",x.detail,"createdAt",x.createdAt));
 }
 @GetMapping("/users") Object users(Authentication auth,@RequestParam(defaultValue="0") int page) {
  var a=access.user(auth); access.require(a,"ADMIN"); return accounts.findAll(page(page)).map(AuthController::profile);
 }
 @PutMapping("/users/{id}") @Transactional
 Object updateUser(Authentication auth,@PathVariable UUID id,@Valid @RequestBody UserUpdate u) {
  var a=access.user(auth); access.require(a,"ADMIN"); if(a.id.equals(id)) throw new ResponseStatusException(HttpStatus.CONFLICT,"Cannot alter your own administrative access");
  var target=accounts.findById(id).orElseThrow(Access::denied); target.role=u.role(); target.enabled=u.enabled(); target.forceReset=u.forceReset(); target.tokenVersion++;
  accounts.save(target); access.audit(a,"USER_UPDATED",id,"Role/status changed; sessions revoked"); return AuthController.profile(target);
 }
 @PostMapping("/users/{id}/reset-token") @Transactional
 Object resetToken(Authentication auth,@PathVariable UUID id) {
  var a=access.user(auth); access.require(a,"ADMIN"); var target=accounts.findById(id).orElseThrow(Access::denied);
  byte[] bytes=new byte[32]; new java.security.SecureRandom().nextBytes(bytes); String token=Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
  var r=new ResetToken(); r.digest=AuthController.digest(token); r.userId=target.id; r.expiresAt=java.time.Instant.now().plusSeconds(900); resets.save(r);
  access.audit(a,"RESET_TOKEN_ISSUED",id,"Single-use token issued for secure out-of-band delivery"); return Map.of("token",token,"expiresAt",r.expiresAt);
 }
}
