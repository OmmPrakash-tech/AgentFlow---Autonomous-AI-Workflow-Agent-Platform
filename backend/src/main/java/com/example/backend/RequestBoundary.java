package com.example.backend;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import tools.jackson.databind.ObjectMapper;
import java.io.*;
import java.util.UUID;

@Component
class RequestBoundary extends OncePerRequestFilter {
 final ObjectMapper json;
 RequestBoundary(ObjectMapper json) { this.json=json; }
 @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain) throws ServletException,IOException {
  String requestId=UUID.randomUUID().toString();
  response.setHeader("X-Request-ID",requestId);
  if(request.getMethod().equals("POST")||request.getMethod().equals("PUT")) {
   byte[] bytes=request.getInputStream().readNBytes(131073);
   if(bytes.length>131072) {
    response.setStatus(413); response.setContentType("application/json");
    response.getWriter().write(json.writeValueAsString(ApiErrors.body(413,"REQUEST_TOO_LARGE","Request exceeds 128 KiB",request.getRequestURI()))); return;
   }
   var wrapper=new HttpServletRequestWrapper(request) {
    @Override public ServletInputStream getInputStream() {
     var input=new ByteArrayInputStream(bytes);
     return new ServletInputStream() {
      public int read(){return input.read();}
      public boolean isFinished(){return input.available()==0;}
      public boolean isReady(){return true;}
      public void setReadListener(ReadListener listener){throw new UnsupportedOperationException();}
     };
    }
    @Override public BufferedReader getReader(){return new BufferedReader(new InputStreamReader(getInputStream(),java.nio.charset.StandardCharsets.UTF_8));}
   };
   chain.doFilter(wrapper,response);
  } else chain.doFilter(request,response);
 }
}
