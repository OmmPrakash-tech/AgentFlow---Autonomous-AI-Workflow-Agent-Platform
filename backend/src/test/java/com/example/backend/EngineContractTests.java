package com.example.backend;

import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.web.server.ResponseStatusException;
import static org.junit.jupiter.api.Assertions.*;

class EngineContractTests {
 @Test void sendsAuthenticatedInternalContractAndReadsState() throws Exception {
  var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
  var observed=new AtomicReference<String>();
  server.createContext("/internal/agent-runs/start",exchange->{
   assertEquals("contract-test-service-key",exchange.getRequestHeaders().getFirst("X-Engine-Key"));
   observed.set(new String(exchange.getRequestBody().readAllBytes(),StandardCharsets.UTF_8));
   byte[] result="{\"status\":\"QUEUED\",\"tool_call_count\":0}".getBytes(StandardCharsets.UTF_8);
   exchange.getResponseHeaders().set("Content-Type","application/json"); exchange.sendResponseHeaders(200,result.length);
   exchange.getResponseBody().write(result); exchange.close();
  });
  server.start();
  try {
   var client=new EngineClient("http://127.0.0.1:"+server.getAddress().getPort(),"contract-test-service-key",new ObjectMapper());
   var result=client.call("POST","/start",Map.of("run_id","test-run","workspace","demo"));
   assertEquals("QUEUED",result.get("status")); assertTrue(observed.get().contains("run_id"));
  } finally { server.stop(0); }
 }
 @Test void unavailableEngineProducesControlledFailure() throws Exception {
  var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
  int port=server.getAddress().getPort(); server.start(); server.stop(0);
  var client=new EngineClient("http://127.0.0.1:"+port,"test-service-key",new ObjectMapper());
  var error=assertThrows(ResponseStatusException.class,()->client.call("GET","/missing/state",null));
  assertEquals(503,error.getStatusCode().value());
 }
}
