package com.example.backend;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import java.time.Instant;
import java.util.Map;

@RestControllerAdvice
class ApiErrors {
 static Map<String,Object> body(int status,String code,String message,String path) {
  return Map.of("timestamp",Instant.now().toString(),"status",status,"code",code,"message",message,"path",path);
 }
 @ExceptionHandler(ResponseStatusException.class)
 ResponseEntity<?> known(ResponseStatusException e,HttpServletRequest r) {
  return ResponseEntity.status(e.getStatusCode()).body(body(e.getStatusCode().value(),"REQUEST_REJECTED",e.getReason()==null?"Request rejected":e.getReason(),r.getRequestURI()));
 }
 @ExceptionHandler({MethodArgumentNotValidException.class,IllegalArgumentException.class,org.springframework.http.converter.HttpMessageNotReadableException.class})
 ResponseEntity<?> invalid(Exception e,HttpServletRequest r) {
  return ResponseEntity.badRequest().body(body(400,"INVALID_INPUT","Input does not match the API schema",r.getRequestURI()));
 }
 @ExceptionHandler(DataIntegrityViolationException.class)
 ResponseEntity<?> conflict(Exception e,HttpServletRequest r) { return ResponseEntity.status(409).body(body(409,"CONFLICT","Resource already exists or is in use",r.getRequestURI())); }
 @ExceptionHandler(Exception.class)
 ResponseEntity<?> other(Exception e,HttpServletRequest r) {
  return ResponseEntity.status(503).body(body(503,"SERVICE_UNAVAILABLE","Operation could not be completed; try again later",r.getRequestURI()));
 }
}
