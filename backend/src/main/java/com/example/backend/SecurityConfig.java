package com.example.backend;

import org.springframework.context.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.web.cors.*;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.List;

@Configuration
class SecurityConfig {
 @Bean PasswordEncoder passwords() { return new BCryptPasswordEncoder(12); }
 @Bean SecretKeySpec jwtKey(@Value("${agentflow.jwt-secret}") String value) {
  if(value.getBytes(StandardCharsets.UTF_8).length<32) throw new IllegalStateException("JWT_SECRET must have at least 32 bytes");
  return new SecretKeySpec(value.getBytes(StandardCharsets.UTF_8),"HmacSHA256");
 }
 @Bean JwtDecoder decoder(SecretKeySpec key) {
  var d=NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
  d.setJwtValidator(JwtValidators.createDefaultWithIssuer("agentflow")); return d;
 }
 @Bean JwtEncoder encoder(SecretKeySpec key) { return new NimbusJwtEncoder(new com.nimbusds.jose.jwk.source.ImmutableSecret<>(key)); }
 @Bean SecurityFilterChain security(HttpSecurity http,@Value("${agentflow.cors-origin}") String origin) throws Exception {
  var cors=new CorsConfiguration(); cors.setAllowedOrigins(List.of(origin));
  cors.setAllowedMethods(List.of("GET","POST","PUT","DELETE","OPTIONS"));
  cors.setAllowedHeaders(List.of("Authorization","Content-Type","Last-Event-ID"));
  var source=new UrlBasedCorsConfigurationSource(); source.registerCorsConfiguration("/**",cors);
  return http.csrf(c->c.disable()).cors(c->c.configurationSource(source))
   .sessionManagement(s->s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
   .authorizeHttpRequests(a->a.requestMatchers("/api/auth/register","/api/auth/login","/api/auth/forgot-password","/api/auth/reset-password","/actuator/health").permitAll().anyRequest().authenticated())
   .oauth2ResourceServer(o->o.jwt(j->{})).build();
 }
}
