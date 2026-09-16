package com.example.backend;

import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.web.context.WebApplicationContext;
import org.springframework.test.web.servlet.*;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import tools.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
class PlatformSecurityTests {
 @Autowired WebApplicationContext context;
 @Autowired ObjectMapper json;
 @Autowired Accounts accounts;
 MockMvc mvc;
 @BeforeEach void setup() throws Exception { mvc=MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).addFilters(context.getBean(RequestBoundary.class)).build(); Files.createDirectories(Path.of("target/test-workspaces/sample")); }
 String register() throws Exception {
  String email=UUID.randomUUID()+"@example.test";
  var r=mvc.perform(post("/api/auth/register").contentType("application/json").content(json.writeValueAsString(Map.of("email",email,"password","test-password-12345")))).andExpect(status().isOk()).andReturn();
  return json.readTree(r.getResponse().getContentAsString()).get("accessToken").asText();
 }
 @Test void rejectsAnonymous() throws Exception { mvc.perform(get("/api/projects")).andExpect(status().isUnauthorized()); }
 @Test void registryChangesRequireAdmin() throws Exception {
  mvc.perform(post("/api/agents").header("Authorization","Bearer "+register()).contentType("application/json").content("{\"name\":\"unsafe\",\"configuration\":{},\"enabled\":true}")).andExpect(status().isForbidden());
 }
 @Test void logoutRevokesToken() throws Exception {
  String token=register(); mvc.perform(post("/api/auth/logout").header("Authorization","Bearer "+token)).andExpect(status().isOk());
  mvc.perform(get("/api/auth/me").header("Authorization","Bearer "+token)).andExpect(status().isForbidden());
 }
 @Test void projectOwnerIsolation() throws Exception {
  String a=register(),b=register();
  String path=UUID.randomUUID().toString(); Files.createDirectories(Path.of("target/test-workspaces",path));
  mvc.perform(post("/api/projects").header("Authorization","Bearer "+a).contentType("application/json").content("{\"name\":\"sample\",\"workspacePath\":\""+path+"\"}")).andExpect(status().isOk());
  mvc.perform(post("/api/projects").header("Authorization","Bearer "+b).contentType("application/json").content("{\"name\":\"duplicate\",\"workspacePath\":\""+path+"\"}")).andExpect(status().isConflict());
  mvc.perform(get("/api/projects").header("Authorization","Bearer "+b)).andExpect(status().isOk()).andExpect(jsonPath("$.totalElements").value(0));
 }
 @Test void rejectsWorkspaceEscape() throws Exception {
  mvc.perform(post("/api/projects").header("Authorization","Bearer "+register()).contentType("application/json").content("{\"name\":\"escape\",\"workspacePath\":\"..\"}")).andExpect(status().isForbidden());
 }
 @Test void profilesNeverExposeHashes() throws Exception {
  mvc.perform(get("/api/auth/me").header("Authorization","Bearer "+register())).andExpect(status().isOk()).andExpect(jsonPath("$.passwordHash").doesNotExist()).andExpect(jsonPath("$.role").value("DEVELOPER"));
 }
 @Test void developerCanCreateWorkflowButCannotOverwriteSharedTemplate() throws Exception {
  String token=register();
  mvc.perform(post("/api/workflows").header("Authorization","Bearer "+token).contentType("application/json").content("{\"name\":\"Personal "+UUID.randomUUID()+"\",\"configuration\":{\"agents\":[\"REPOSITORY\",\"REVIEWER\"]},\"enabled\":true}")).andExpect(status().isOk());
  mvc.perform(post("/api/workflows").header("Authorization","Bearer "+token).contentType("application/json").content("{\"name\":\"Security Audit\",\"configuration\":{\"agents\":[\"REPOSITORY\"]},\"enabled\":true}")).andExpect(status().isForbidden());
 }
 @Test void invalidWorkflowIsRejected() throws Exception {
  mvc.perform(post("/api/workflows").header("Authorization","Bearer "+register()).contentType("application/json").content("{\"name\":\"Invalid\",\"configuration\":{\"agents\":[\"UNKNOWN\"]},\"enabled\":true}")).andExpect(status().isBadRequest());
 }
 @Test void wrongPasswordAndPrivilegeEscalationAreRejected() throws Exception {
  String token=register();
  mvc.perform(post("/api/auth/password").header("Authorization","Bearer "+token).contentType("application/json").content("{\"currentPassword\":\"wrong\",\"newPassword\":\"new-test-password-123\"}")).andExpect(status().isForbidden());
  mvc.perform(get("/api/users").header("Authorization","Bearer "+token)).andExpect(status().isForbidden());
 }
 @Test void oversizedRequestIsRejectedBeforeParsing() throws Exception {
  mvc.perform(post("/api/auth/register").contentType("application/json").content("x".repeat(131073))).andExpect(status().isPayloadTooLarge());
 }
}
