package com.example.backend;

import org.springframework.stereotype.Service;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
import java.util.*;

@Service
class Access {
 final Accounts accounts;
 final Audits audits;
 Access(Accounts accounts,Audits audits) { this.accounts=accounts; this.audits=audits; }
 Account user(Authentication auth) {
  if(auth==null || !(auth.getPrincipal() instanceof Jwt jwt)) throw denied();
  var a=accounts.findById(UUID.fromString(jwt.getSubject())).orElseThrow(Access::denied);
  if(!a.enabled || a.tokenVersion != ((Number)jwt.getClaim("version")).intValue()) throw denied();
  return a;
 }
 void require(Account a,String permission) {
  if(a.forceReset) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"Password change required");
  boolean allowed=a.role.equals("ADMIN") || switch(permission) {
   case "READ" -> true;
   case "EXECUTE","APPROVE" -> Set.of("DEVELOPER","ANALYST").contains(a.role);
   case "WRITE","EDIT" -> a.role.equals("DEVELOPER");
   default -> false;
  };
  if(!allowed) throw denied();
 }
 void owns(Account a,UUID owner) { if(!a.role.equals("ADMIN")&&!a.id.equals(owner)) throw denied(); }
 void audit(Account a,String action,Object resource,String detail) {
  var x=new Audit(); x.actorId=a==null?null:a.id; x.action=action; x.resource=String.valueOf(resource); x.detail=detail; audits.save(x);
 }
 static ResponseStatusException denied() { return new ResponseStatusException(HttpStatus.FORBIDDEN,"Permission denied"); }
}
