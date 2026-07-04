package com.ewolff.microservice.order.logic;

import java.util.List;

/**
 * JSON request body for creating an Order via {@link OrderJsonController}.
 * Kept separate from the JPA {@link Order} entity so the public JSON contract
 * of this endpoint stays stable independent of persistence details.
 */
public class OrderRequest {

	private long customerId;

	private List<OrderLineRequest> orderLine;

	public long getCustomerId() {
		return customerId;
	}

	public void setCustomerId(long customerId) {
		this.customerId = customerId;
	}

	public List<OrderLineRequest> getOrderLine() {
		return orderLine;
	}

	public void setOrderLine(List<OrderLineRequest> orderLine) {
		this.orderLine = orderLine;
	}

	public static class OrderLineRequest {

		private long itemId;

		private int count;

		public long getItemId() {
			return itemId;
		}

		public void setItemId(long itemId) {
			this.itemId = itemId;
		}

		public int getCount() {
			return count;
		}

		public void setCount(int count) {
			this.count = count;
		}
	}
}
