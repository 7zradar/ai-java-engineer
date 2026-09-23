package com.example.demo.controller;

import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class OrderControllerTest {
    @Test
    void testGetOrdersSuccess() {
        OrderController controller = new OrderController();
        ResponseEntity<List<String>> response = controller.getOrders(101L);
        assertEquals(200, response.getStatusCode().value());
        assertFalse(response.getBody().isEmpty());
    }
}
