package com.example.backend;

import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
import tools.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.Map;

@Component
class EngineClient {
 final HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
 final String base,secret; final ObjectMapper json;
 EngineClient(@Value("${agentflow.engine-url}") String base,@Value("${agentflow.engine-secret}") String secret,ObjectMapper json) { this.base=base; this.secret=secret; this.json=json; }
 Map<String,Object> call(String method,String path,Object data) {
  try {
   var b=HttpRequest.newBuilder(URI.create(base+"/internal/agent-runs"+path)).timeout(Duration.ofSeconds(8)).header("X-Engine-Key",secret).header("Content-Type","application/json");
   b.method(method,data==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(json.writeValueAsString(data)));
   var response=client.send(b.build(),HttpResponse.BodyHandlers.ofString());
   if(response.statusCode()>=400) throw new ResponseStatusException(response.statusCode()==409?HttpStatus.CONFLICT:HttpStatus.BAD_GATEWAY,"Agent engine rejected the request");
   return json.readValue(response.body(),Map.class);
  } catch(ResponseStatusException e) { throw e; } catch(Exception e) { throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Agent engine unavailable"); }
 }
}
