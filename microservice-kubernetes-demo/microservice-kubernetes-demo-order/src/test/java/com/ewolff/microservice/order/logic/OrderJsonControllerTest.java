package com.ewolff.microservice.order.logic;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import com.ewolff.microservice.order.OrderApp;

/**
 * Integration test for the JSON /orders endpoint (task order-json-endpoint),
 * exercising real HTTP + JSON (de)serialization against the CatalogStub
 * (valid item id = 1) and CustomerStub (valid customer id = 42) test doubles.
 *
 * Note: each POST /orders call is a real HTTP request handled in its own
 * server-side transaction, so @Transactional on the test method would NOT
 * roll it back (same reason OrderWebIntegrationTest cleans up manually via
 * orderRepository.deleteAll() instead of relying on transactional rollback).
 * This test does the same via an @After cleanup to avoid leaking Order rows
 * for customerId=42 into other test classes sharing the same in-memory DB.
 */
@RunWith(SpringJUnit4ClassRunner.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.DEFINED_PORT, classes = OrderApp.class)
@ActiveProfiles("test")
public class OrderJsonControllerTest {

	private static final long VALID_CUSTOMER_ID = 42L;
	private static final long VALID_ITEM_ID = 1L;
	private static final long INVALID_ITEM_ID = 999L;

	private RestTemplate restTemplate = new RestTemplate();

	@Value("${server.port}")
	private long serverPort;

	@Autowired
	private OrderRepository orderRepository;

	private String ordersURL() {
		return "http://localhost:" + serverPort + "/orders";
	}

	@After
	public void cleanup() {
		orderRepository.deleteAll();
	}

	@Test
	public void createsOrderWithValidCustomerAndItem() {
		OrderRequest request = new OrderRequest();
		request.setCustomerId(VALID_CUSTOMER_ID);
		OrderRequest.OrderLineRequest line = new OrderRequest.OrderLineRequest();
		line.setItemId(VALID_ITEM_ID);
		line.setCount(2);
		request.setOrderLine(java.util.Collections.singletonList(line));

		ResponseEntity<OrderResponse> response = restTemplate.postForEntity(ordersURL(), request, OrderResponse.class);

		assertEquals(HttpStatus.CREATED, response.getStatusCode());
		assertEquals(VALID_CUSTOMER_ID, response.getBody().getCustomerId());
		assertEquals(1, response.getBody().getOrderLine().size());
		assertEquals(VALID_ITEM_ID, response.getBody().getOrderLine().get(0).getItemId());
	}

	@Test
	public void rejectsOrderWithInvalidItem() {
		OrderRequest request = new OrderRequest();
		request.setCustomerId(VALID_CUSTOMER_ID);
		OrderRequest.OrderLineRequest line = new OrderRequest.OrderLineRequest();
		line.setItemId(INVALID_ITEM_ID);
		line.setCount(1);
		request.setOrderLine(java.util.Collections.singletonList(line));

		try {
			restTemplate.postForEntity(ordersURL(), request, OrderResponse.class);
			org.junit.Assert.fail("Expected HttpClientErrorException (400)");
		} catch (HttpClientErrorException e) {
			assertEquals(HttpStatus.BAD_REQUEST, e.getStatusCode());
			assertTrue(e.getResponseBodyAsString().contains("Item does not exist"));
		}
	}

	@Test
	public void getReturnsCreatedOrder() {
		OrderRequest request = new OrderRequest();
		request.setCustomerId(VALID_CUSTOMER_ID);
		OrderRequest.OrderLineRequest line = new OrderRequest.OrderLineRequest();
		line.setItemId(VALID_ITEM_ID);
		line.setCount(3);
		request.setOrderLine(java.util.Collections.singletonList(line));

		OrderResponse created = restTemplate.postForEntity(ordersURL(), request, OrderResponse.class).getBody();

		OrderResponse fetched = restTemplate.getForObject(ordersURL() + "/" + created.getId(), OrderResponse.class);

		assertEquals(created.getId(), fetched.getId());
		assertEquals(VALID_CUSTOMER_ID, fetched.getCustomerId());
	}
}
