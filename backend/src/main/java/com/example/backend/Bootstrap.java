package com.example.backend;

import org.springframework.stereotype.Component;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.ApplicationArguments;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import tools.jackson.databind.ObjectMapper;
import java.util.*;

@Component
class Bootstrap implements ApplicationRunner {
 final Accounts accounts; final Definitions definitions; final PasswordEncoder passwords; final ObjectMapper json; final String email,password; final WorkspaceGuards guards;
 Bootstrap(Accounts a,Definitions d,PasswordEncoder p,ObjectMapper j,WorkspaceGuards guards,@Value("${agentflow.bootstrap-email:}") String email,@Value("${agentflow.bootstrap-password:}") String password) { accounts=a; definitions=d; passwords=p; json=j; this.guards=guards; this.email=email; this.password=password; }
 void seed(String kind,String name,Map<String,Object> config) {
  if(definitions.findByKindAndName(kind,name).isPresent()) return;
  var d=new Definition(); d.kind=kind; d.name=name; d.configuration=json.writeValueAsString(config); definitions.save(d);
 }
 public void run(ApplicationArguments args) {
  if(!guards.existsById(1)) guards.save(new WorkspaceGuard());
  if(!email.isBlank()&&accounts.findByEmail(AuthController.normalize(email)).isEmpty()) {
   if(password.length()<16) throw new IllegalStateException("Bootstrap password requires 16 characters");
   var a=new Account(); a.email=AuthController.normalize(email); a.passwordHash=passwords.encode(password); a.role="ADMIN"; a.forceReset=true; accounts.save(a);
  }
  var reads=List.of("list_files","read_file","search_code","inspect_project","inspect_dependencies","security_scan","inspect_git_diff");
  for(String name:List.of("PLANNER","RESEARCH","REPOSITORY","CODE_ANALYST","SECURITY","DEVELOPER","TESTER","DEBUGGER","REVIEWER","REPORTER")) {
   var tools=new ArrayList<>(reads); if(name.equals("DEVELOPER")) tools.add("modify_file"); if(name.equals("TESTER")||name.equals("DEBUGGER")) tools.add("run_tests");
   seed("AGENT",name,Map.of("description",name+" specialist","model","qwen3:8b","available_tools",tools,"risk_level",name.equals("DEVELOPER")?"MEDIUM":"LOW","max_iterations",4,"timeout",180));
  }
  for(String tool:List.of("list_files","read_file","search_code","inspect_project","inspect_dependencies","security_scan","inspect_git_diff","modify_file","run_tests"))
   seed("TOOL",tool,Map.of("description",tool.replace('_',' '),"risk_level",tool.equals("modify_file")?"MEDIUM":tool.equals("run_tests")?"HIGH":"LOW","timeout",60,"permissions",List.of(tool.equals("modify_file")?"EDIT":"READ")));
  for(String name:List.of("Production Readiness Audit","Test Failure Investigation","Security Audit","API Review"))
   seed("WORKFLOW",name,Map.of("objective",name,"agents",name.equals("Test Failure Investigation")?List.of("REPOSITORY","TESTER","DEBUGGER","DEVELOPER","TESTER","REVIEWER","REPORTER"):List.of("REPOSITORY","CODE_ANALYST","SECURITY","REVIEWER","REPORTER")));
 }
}
