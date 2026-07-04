package com.ewolff.microservice.order.logic;

import java.util.List;
import java.util.stream.Collectors;

/**
 * JSON response body returned by {@link OrderJsonController}. Kept separate
 * from the JPA {@link Order} entity so the public JSON contract of this
 * endpoint stays stable independent of persistence details.
 */
public class OrderResponse {

	private long id;

	private long customerId;

	private List<OrderLineResponse> orderLine;

	public OrderResponse() {
	}

	public OrderResponse(Order order) {
		this.id = order.getId();
		this.customerId = order.getCustomerId();
		this.orderLine = order.getOrderLine().stream()
				.map(OrderLineResponse::new)
				.collect(Collectors.toList());
	}

	public long getId() {
		return id;
	}

	public long getCustomerId() {
		return customerId;
	}

	public List<OrderLineResponse> getOrderLine() {
		return orderLine;
	}

	public static class OrderLineResponse {

		private long itemId;

		private int count;

		public OrderLineResponse() {
		}

		public OrderLineResponse(OrderLine orderLine) {
			this.itemId = orderLine.getItemId();
			this.count = orderLine.getCount();
		}

		public long getItemId() {
			return itemId;
		}

		public int getCount() {
			return count;
		}
	}
}
