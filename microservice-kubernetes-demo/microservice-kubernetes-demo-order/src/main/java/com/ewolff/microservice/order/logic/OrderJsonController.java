package com.ewolff.microservice.order.logic;

import java.util.NoSuchElementException;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * JSON REST endpoint for creating and reading Orders, used by the
 * Function Calling and MCP integrations (see llm-integrations/).
 *
 * This exists as a separate controller (mapped to "/orders", plural)
 * because the existing HTML {@link OrderController} maps bare paths
 * ("/", "/{id}") that collide with and shadow the Spring Data REST JSON
 * endpoints Spring would otherwise expose at "/order" and "/order/{id}"
 * via {@link OrderRepository}. See llm-integrations/experiments/baseline_contracts.md
 * for the confirmed routing collision (GET /order -> HTTP 400, GET /1 -> HTTP 500).
 */
@RestController
@RequestMapping("/orders")
class OrderJsonController {

	private final OrderService orderService;

	private final OrderRepository orderRepository;

	@Autowired
	OrderJsonController(OrderService orderService, OrderRepository orderRepository) {
		this.orderService = orderService;
		this.orderRepository = orderRepository;
	}

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public OrderResponse create(@RequestBody OrderRequest request) {
		Order order = new Order(request.getCustomerId());
		if (request.getOrderLine() != null) {
			request.getOrderLine().forEach(
					line -> order.addLine(line.getCount(), line.getItemId()));
		}
		Order saved = orderService.order(order);
		return new OrderResponse(saved);
	}

	@GetMapping("/{id}")
	public OrderResponse get(@PathVariable("id") long id) {
		return orderRepository.findById(id).map(OrderResponse::new)
				.orElseThrow(NoSuchElementException::new);
	}

	@GetMapping
	public java.util.List<OrderResponse> list() {
		return java.util.stream.StreamSupport
				.stream(orderRepository.findAll().spliterator(), false)
				.map(OrderResponse::new)
				.collect(Collectors.toList());
	}

	@ExceptionHandler(IllegalArgumentException.class)
	@ResponseStatus(HttpStatus.BAD_REQUEST)
	public ResponseEntity<ErrorResponse> handleInvalidOrder(IllegalArgumentException e) {
		return ResponseEntity.status(HttpStatus.BAD_REQUEST)
				.body(new ErrorResponse(e.getMessage()));
	}

	@ExceptionHandler(NoSuchElementException.class)
	@ResponseStatus(HttpStatus.NOT_FOUND)
	public ResponseEntity<ErrorResponse> handleNotFound() {
		return ResponseEntity.status(HttpStatus.NOT_FOUND)
				.body(new ErrorResponse("Order not found"));
	}

	public static class ErrorResponse {

		private final String error;

		public ErrorResponse(String error) {
			this.error = error;
		}

		public String getError() {
			return error;
		}
	}
}
