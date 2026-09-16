package com.example.backend;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;
import org.springframework.http.*;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;
import java.util.*;
import java.time.Instant;

@RestController @RequestMapping("/api")
class RunController {
 record Start(@NotNull UUID projectId,@NotBlank @Size(max=4000) String objective,@Pattern(regexp="READ_ONLY|EDIT_MODE") @NotNull String mode,UUID workflowId) {}
 record Decision(@NotBlank String approvalId,boolean approved) {}
 final Access access; final Projects projects; final Runs runs; final Definitions definitions; final EngineClient engine; final ObjectMapper json; final RateLimits limits;
 RunController(Access a,Projects p,Runs r,Definitions d,EngineClient e,ObjectMapper j,RateLimits l) { access=a; projects=p; runs=r; definitions=d; engine=e; json=j; limits=l; }
 Run owned(Authentication auth,UUID id,String permission) {
  var a=access.user(auth); access.require(a,permission); var r=runs.findById(id).orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND)); access.owns(a,r.ownerId); return r;
 }
 Map<String,Object> dto(Run r) { return Map.of("id",r.id,"projectId",r.projectId,"objective",r.objective,"status",r.status,"mode",r.mode,"createdAt",r.createdAt,"updatedAt",r.updatedAt,"state",json.readValue(r.snapshot,Map.class)); }
 Run sync(Run r) {
  try { var state=engine.call("GET","/"+r.id+"/state",null); r.snapshot=json.writeValueAsString(state); r.status=String.valueOf(state.get("status")); r.updatedAt=Instant.now(); return runs.save(r); }
  catch(ResponseStatusException e) { return r; }
 }
 @GetMapping("/runs") Object list(Authentication auth,@RequestParam(defaultValue="0") int page) {
  var a=access.user(auth); access.require(a,"READ"); return (a.role.equals("ADMIN")?runs.findAll(PlatformController.page(page)):runs.findByOwnerId(a.id,PlatformController.page(page))).map(this::dto);
 }
 @GetMapping("/runs/{id}") Object get(Authentication auth,@PathVariable UUID id) { return dto(sync(owned(auth,id,"READ"))); }
 @PostMapping("/runs") Object start(Authentication auth,@Valid @RequestBody Start input) {
  var a=access.user(auth); access.require(a,input.mode().equals("EDIT_MODE")?"EDIT":"EXECUTE"); limits.check("runs:"+a.id,5);
  var p=projects.findById(input.projectId()).orElseThrow(Access::denied); access.owns(a,p.ownerId);
  var r=new Run(); r.projectId=p.id; r.ownerId=a.id; r.objective=input.objective(); r.mode=input.mode();
  var payload=new HashMap<String,Object>(); payload.put("run_id",r.id); payload.put("project_id",p.id); payload.put("objective",r.objective); payload.put("workspace",p.workspacePath); payload.put("mode",r.mode);
  payload.put("agents",definitions.findByKindOrderByName("AGENT").stream().filter(d->d.enabled).map(d->Map.of("name",d.name,"configuration",json.readValue(d.configuration,Map.class))).toList());
  payload.put("tools",definitions.findByKindOrderByName("TOOL").stream().filter(d->d.enabled).map(d->d.name).toList());
  if(input.workflowId()!=null) {
   var w=definitions.findById(input.workflowId()).orElseThrow(Access::denied); if(!w.kind.equals("WORKFLOW")||!w.enabled) throw Access.denied();
   if(w.ownerId!=null) access.owns(a,w.ownerId);
   payload.put("workflow",json.readValue(w.configuration,Map.class));
  }
  runs.saveAndFlush(r); access.audit(a,"RUN_REQUESTED",r.id,r.mode);
  try { var state=engine.call("POST","/start",payload); r.snapshot=json.writeValueAsString(state); r.status=String.valueOf(state.get("status")); }
  catch(ResponseStatusException e) { r.status="FAILED"; r.snapshot=json.writeValueAsString(Map.of("error","ENGINE_UNAVAILABLE","status","FAILED")); runs.save(r); throw e; }
  return dto(runs.save(r));
 }
 @PostMapping("/runs/{id}/cancel") Object cancel(Authentication auth,@PathVariable UUID id) {
  var r=owned(auth,id,"EXECUTE"); engine.call("POST","/"+id+"/cancel",Map.of()); access.audit(access.user(auth),"RUN_CANCELLED",id,"Cancellation requested"); return dto(sync(r));
 }
 @PostMapping("/runs/{id}/approval") Object decide(Authentication auth,@PathVariable UUID id,@Valid @RequestBody Decision d) {
  var r=owned(auth,id,"APPROVE");
  engine.call("POST","/"+id+"/resume",Map.of("approval_id",d.approvalId(),"approved",d.approved()));
  access.audit(access.user(auth),d.approved()?"APPROVAL_GRANTED":"APPROVAL_REJECTED",id,d.approvalId()); return dto(sync(r));
 }
 @GetMapping(value="/runs/{id}/events",produces=MediaType.TEXT_EVENT_STREAM_VALUE)
 String events(Authentication auth,@PathVariable UUID id) {
  var r=sync(owned(auth,id,"READ"));
  // A finite SSE response allows authenticated fetch clients to reconnect without query-string tokens.
  return "event: state\ndata: "+json.writeValueAsString(dto(r))+"\n\n";
 }
 @GetMapping(value="/runs/{id}/report",produces="text/markdown")
 String report(Authentication auth,@PathVariable UUID id) {
  var r=sync(owned(auth,id,"READ")); var state=json.readValue(r.snapshot,Map.class);
  return String.valueOf(state.getOrDefault("report","# Report not available\nRun status: "+r.status));
 }
}
