package com.example.backend;

import org.springframework.stereotype.Component;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.*;
import java.util.List;

@Configuration @EnableScheduling
class Scheduling {}
@Component
class RunSynchronizer {
 final Runs runs; final RunController controller;
 RunSynchronizer(Runs r,RunController c) { runs=r; controller=c; }
 @Scheduled(fixedDelay=5000)
 void sync() {
  for(var r:runs.findTop20ByStatusInOrderByCreatedAtAsc(List.of("QUEUED","PLANNING","RUNNING","WAITING_APPROVAL","VERIFYING"))) {
   try { controller.sync(r); } catch(Exception ignored) { /* Preserve the last durable snapshot on transient failure. */ }
  }
 }
}
