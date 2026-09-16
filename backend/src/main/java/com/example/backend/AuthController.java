package com.example.backend;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import java.time.Instant;
import java.util.*;
import java.security.*;
import java.nio.charset.StandardCharsets;

@RestController @RequestMapping("/api/auth")
class AuthController {
 record Credentials(@Email @NotBlank @Size(max=254) String email,@Size(min=12,max=72) String password) {}
 record Change(@NotBlank String currentPassword,@Size(min=12,max=72) String newPassword) {}
 record EmailRequest(@Email @NotBlank String email) {}
 record Reset(@NotBlank String token,@Size(min=12,max=72) String password) {}
 final Accounts accounts; final Access access; final PasswordEncoder passwords; final JwtEncoder encoder; final RateLimits limits; final ResetTokens resets;
 AuthController(Accounts a,Access access,PasswordEncoder p,JwtEncoder e,RateLimits l,ResetTokens resets) { accounts=a; this.access=access; passwords=p; encoder=e; limits=l; this.resets=resets; }
 static String normalize(String e) { return e.strip().toLowerCase(Locale.ROOT); }
 static Map<String,Object> profile(Account a) { return Map.of("id",a.id,"email",a.email,"role",a.role,"enabled",a.enabled,"forceReset",a.forceReset); }
 Map<String,Object> session(Account a) {
  var now=Instant.now();
  var claims=JwtClaimsSet.builder().issuer("agentflow").subject(a.id.toString()).issuedAt(now).expiresAt(now.plusSeconds(1800)).claim("version",a.tokenVersion).build();
  String token=encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(),claims)).getTokenValue();
  return Map.of("accessToken",token,"expiresIn",1800,"user",profile(a));
 }
 @PostMapping("/register") @Transactional
 Map<String,Object> register(@Valid @RequestBody Credentials c,HttpServletRequest req) {
  limits.check("auth:"+req.getRemoteAddr(),10);
  var a=new Account(); a.email=normalize(c.email()); a.passwordHash=passwords.encode(c.password()); accounts.saveAndFlush(a);
  access.audit(a,"REGISTER",a.id,"Account registered"); return session(a);
 }
 @PostMapping("/login")
 Map<String,Object> login(@Valid @RequestBody Credentials c,HttpServletRequest req) {
  limits.check("auth:"+req.getRemoteAddr(),10);
  var a=accounts.findByEmail(normalize(c.email())).orElse(null);
  // Always perform a bcrypt comparison, including nonexistent accounts.
  String hash=a==null?"$2a$12$9SOTlFGgBbQIAa92myfs5e0jcEztIZL.w8kPLKghMm.BmQ.zFwKLa":a.passwordHash;
  boolean valid=passwords.matches(c.password(),hash);
  if(a==null||!valid||!a.enabled) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"Invalid credentials");
  access.audit(a,"LOGIN",a.id,"Successful login"); return session(a);
 }
 @GetMapping("/me") Map<String,Object> me(Authentication auth) { return profile(access.user(auth)); }
 @PostMapping("/logout") @Transactional
 Map<String,String> logout(Authentication auth) { var a=access.user(auth); a.tokenVersion++; accounts.save(a); return Map.of("status","SIGNED_OUT"); }
 @PostMapping("/password") @Transactional
 Map<String,String> change(Authentication auth,@Valid @RequestBody Change c) {
  var a=access.user(auth); if(!passwords.matches(c.currentPassword(),a.passwordHash)) throw Access.denied();
  a.passwordHash=passwords.encode(c.newPassword()); a.tokenVersion++; a.forceReset=false; accounts.save(a);
  access.audit(a,"PASSWORD_CHANGED",a.id,"Sessions revoked"); return Map.of("status","PASSWORD_CHANGED");
 }
 @PostMapping("/forgot-password")
 Map<String,String> forgot(@Valid @RequestBody EmailRequest e,HttpServletRequest req) {
  limits.check("auth:"+req.getRemoteAddr(),10);
  // Delivery is deliberately operator-assisted until a mail provider is configured.
  accounts.findByEmail(normalize(e.email())).ifPresent(a->access.audit(a,"RESET_REQUESTED",a.id,"Administrator-assisted password reset requested"));
  return Map.of("message","If the account exists, a reset request has been recorded. Contact your administrator.");
 }
 static String digest(String token) {
  try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8))); }
  catch(NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
 }
 @PostMapping("/reset-password") @Transactional
 Map<String,String> reset(@Valid @RequestBody Reset r,HttpServletRequest req) {
  limits.check("auth:"+req.getRemoteAddr(),10);
  var t=resets.findById(digest(r.token())).orElseThrow(Access::denied);
  if(t.used||t.expiresAt.isBefore(Instant.now())) throw Access.denied();
  t.used=true; resets.save(t); var a=accounts.findById(t.userId).orElseThrow(Access::denied);
  a.passwordHash=passwords.encode(r.password()); a.forceReset=false; a.tokenVersion++; accounts.save(a);
  access.audit(a,"PASSWORD_RESET",a.id,"Sessions revoked"); return Map.of("status","PASSWORD_CHANGED");
 }
}
