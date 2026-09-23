package com.example.demo.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.List;

@RestController
@RequestMapping("/api/v1/customers")
public class OrderController {
    @GetMapping("/{id}/orders")
    public ResponseEntity<List<String>> getOrders(@PathVariable Long id) {
        return ResponseEntity.ok(List.of("ORDER-1001", "ORDER-1002"));
    }
}
