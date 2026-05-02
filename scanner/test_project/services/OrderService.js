/**
 * Order Service
 * Handles order processing and management
 */

const ProductService = require('./ProductService');
const InventoryService = require('./InventoryService');

class OrderService {
  constructor() {
    this.orders = new Map();
  }

  /**
   * Get all orders with product details
   */
  async getAllOrders() {
    const orders = Array.from(this.orders.values());
    
    // Enrich orders with product data (circular dependency)
    const enriched = await Promise.all(
      orders.map(async (order) => {
        const items = await Promise.all(
          order.items.map(async (item) => {
            const product = await ProductService.getProductById(item.productId);
            return {
              ...item,
              productDetails: product,
            };
          })
        );
        
        return {
          ...order,
          items,
        };
      })
    );
    
    return enriched;
  }

  /**
   * Get order by ID
   */
  async getOrderById(orderId) {
    const order = this.orders.get(orderId);
    if (!order) {
      return null;
    }

    // Enrich with product details
    const items = await Promise.all(
      order.items.map(async (item) => ({
        ...item,
        productDetails: await ProductService.getProductById(item.productId),
      }))
    );

    return {
      ...order,
      items,
    };
  }

  /**
   * Create new order
   */
  async createOrder(orderData) {
    // Validate products and check inventory
    for (const item of orderData.items) {
      const product = await ProductService.getProductById(item.productId);
      if (!product) {
        throw new Error(`Product ${item.productId} not found`);
      }

      const stock = await InventoryService.getStockLevel(item.productId);
      if (stock.quantity < item.quantity) {
        throw new Error(`Insufficient stock for product ${product.name}`);
      }
    }

    const order = {
      id: `order_${Date.now()}`,
      customerId: orderData.customerId,
      items: orderData.items,
      status: 'pending',
      totalAmount: await this.calculateTotal(orderData.items),
      createdAt: new Date().toISOString(),
    };

    this.orders.set(order.id, order);

    // Reserve inventory
    for (const item of order.items) {
      await InventoryService.reserveStock(item.productId, item.quantity);
    }

    return order;
  }

  /**
   * Calculate order total
   */
  async calculateTotal(items) {
    let total = 0;
    for (const item of items) {
      const product = await ProductService.getProductById(item.productId);
      total += product.price * item.quantity;
    }
    return total;
  }

  /**
   * Update order status
   */
  async updateOrderStatus(orderId, status) {
    const order = this.orders.get(orderId);
    if (!order) {
      throw new Error('Order not found');
    }

    const updated = {
      ...order,
      status,
      updatedAt: new Date().toISOString(),
    };

    // If order is completed, deduct from inventory
    if (status === 'completed' && order.status !== 'completed') {
      for (const item of order.items) {
        await InventoryService.deductStock(item.productId, item.quantity);
      }
    }

    // If order is cancelled, release reserved inventory
    if (status === 'cancelled' && order.status !== 'cancelled') {
      for (const item of order.items) {
        await InventoryService.releaseReservedStock(item.productId, item.quantity);
      }
    }

    this.orders.set(orderId, updated);
    return updated;
  }

  /**
   * Get orders by customer
   */
  async getOrdersByCustomer(customerId) {
    const orders = Array.from(this.orders.values()).filter(
      (o) => o.customerId === customerId
    );

    return Promise.all(
      orders.map(async (order) => ({
        ...order,
        items: await Promise.all(
          order.items.map(async (item) => ({
            ...item,
            productDetails: await ProductService.getProductById(item.productId),
          }))
        ),
      }))
    );
  }

  /**
   * Get order count for a product
   */
  async getOrderCountForProduct(productId) {
    let count = 0;
    for (const order of this.orders.values()) {
      if (order.items.some((item) => item.productId === productId)) {
        count++;
      }
    }
    return count;
  }

  /**
   * Get recent orders for a product
   */
  async getRecentOrdersForProduct(productId, limit = 5) {
    const orders = Array.from(this.orders.values())
      .filter((order) => order.items.some((item) => item.productId === productId))
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
      .slice(0, limit);

    return orders;
  }

  /**
   * Get pending orders for a product
   */
  async getPendingOrdersForProduct(productId) {
    return Array.from(this.orders.values()).filter(
      (order) =>
        order.status === 'pending' &&
        order.items.some((item) => item.productId === productId)
    );
  }

  /**
   * Get order statistics
   */
  async getOrderStatistics() {
    const orders = Array.from(this.orders.values());
    
    const stats = {
      total: orders.length,
      pending: orders.filter((o) => o.status === 'pending').length,
      completed: orders.filter((o) => o.status === 'completed').length,
      cancelled: orders.filter((o) => o.status === 'cancelled').length,
      totalRevenue: orders
        .filter((o) => o.status === 'completed')
        .reduce((sum, o) => sum + o.totalAmount, 0),
    };

    return stats;
  }

  /**
   * Cancel order
   */
  async cancelOrder(orderId) {
    return this.updateOrderStatus(orderId, 'cancelled');
  }

  /**
   * Complete order
   */
  async completeOrder(orderId) {
    return this.updateOrderStatus(orderId, 'completed');
  }
}

module.exports = new OrderService();

// Made with Bob
