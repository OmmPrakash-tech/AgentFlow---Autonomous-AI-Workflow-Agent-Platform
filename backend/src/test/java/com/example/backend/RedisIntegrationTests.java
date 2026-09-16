package com.example.backend;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.server.ResponseStatusException;
import java.util.UUID;
import static org.junit.jupiter.api.Assertions.*;

@EnabledIfSystemProperty(named="run.redis.integration", matches="true")
class RedisIntegrationTests {
 @Test void enforcesAtomicLimitWithRealRedis() {
  var factory=new LettuceConnectionFactory("localhost",6379);
  factory.afterPropertiesSet(); factory.start();
  try {
   var template=new StringRedisTemplate(factory);
   var limits=new RateLimits(template,true);
   String key="integration:"+UUID.randomUUID();
   limits.check(key,2); limits.check(key,2);
   var error=assertThrows(ResponseStatusException.class,()->limits.check(key,2));
   assertEquals(429,error.getStatusCode().value());
   assertTrue(template.getExpire("agentflow:rate:"+key)>0);
   template.delete("agentflow:rate:"+key);
  } finally { factory.destroy(); }
 }
}
