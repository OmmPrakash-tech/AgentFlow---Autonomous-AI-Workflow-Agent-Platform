package com.example.backend;

import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
import java.util.List;

@Component
class RateLimits {
 final StringRedisTemplate redis; final boolean enabled;
 RateLimits(StringRedisTemplate redis,@Value("${agentflow.redis-enabled:true}") boolean enabled) { this.redis=redis; this.enabled=enabled; }
 void check(String key,int limit) {
  if(!enabled) return;
  try {
   Long count=redis.execute(new DefaultRedisScript<Long>("local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n",Long.class),List.of("agentflow:rate:"+key));
   if(count!=null&&count>limit) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS,"Rate limit exceeded");
  } catch(ResponseStatusException e) { throw e; }
  catch(Exception e) { throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Rate limiter unavailable"); }
 }
}
