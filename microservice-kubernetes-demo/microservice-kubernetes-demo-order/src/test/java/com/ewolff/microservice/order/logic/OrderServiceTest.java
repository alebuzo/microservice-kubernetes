package com.ewolff.microservice.order.logic;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import org.junit.Before;
import org.junit.Test;

import com.ewolff.microservice.order.clients.CatalogClient;
import com.ewolff.microservice.order.clients.CustomerClient;

public class OrderServiceTest {

	private static final long VALID_CUSTOMER_ID = 1L;
	private static final long INVALID_CUSTOMER_ID = 999L;
	private static final long VALID_ITEM_ID = 1L;
	private static final long INVALID_ITEM_ID = 999L;

	private OrderRepository orderRepository;
	private CustomerClient customerClient;
	private CatalogClient itemClient;
	private OrderService orderService;

	@Before
	public void setup() {
		orderRepository = mock(OrderRepository.class);
		customerClient = mock(CustomerClient.class);
		itemClient = mock(CatalogClient.class);
		orderService = new OrderService(orderRepository, customerClient, itemClient);

		when(customerClient.isValidCustomerId(VALID_CUSTOMER_ID)).thenReturn(true);
		when(customerClient.isValidCustomerId(INVALID_CUSTOMER_ID)).thenReturn(false);
		when(itemClient.exists(VALID_ITEM_ID)).thenReturn(true);
		when(itemClient.exists(INVALID_ITEM_ID)).thenReturn(false);
		when(orderRepository.save(org.mockito.ArgumentMatchers.any(Order.class)))
				.thenAnswer(invocation -> invocation.getArgument(0));
	}

	@Test
	public void orderWithNoLinesIsRejected() {
		Order order = new Order(VALID_CUSTOMER_ID);
		assertThrows(IllegalArgumentException.class, () -> orderService.order(order));
	}

	@Test
	public void orderWithInvalidCustomerIsRejected() {
		Order order = new Order(INVALID_CUSTOMER_ID);
		order.addLine(1, VALID_ITEM_ID);
		assertThrows(IllegalArgumentException.class, () -> orderService.order(order));
	}

	@Test
	public void orderWithInvalidItemIsRejected() {
		Order order = new Order(VALID_CUSTOMER_ID);
		order.addLine(1, INVALID_ITEM_ID);
		assertThrows(IllegalArgumentException.class, () -> orderService.order(order));
	}

	@Test
	public void orderWithValidCustomerAndItemsIsSaved() {
		Order order = new Order(VALID_CUSTOMER_ID);
		order.addLine(2, VALID_ITEM_ID);
		Order saved = orderService.order(order);
		assertEquals(VALID_CUSTOMER_ID, saved.getCustomerId());
	}
}
