/**
 * Inventory Service
 * Handles stock management and inventory tracking
 */

const ProductService = require('./ProductService');
const OrderService = require('./OrderService');

class InventoryService {
  constructor() {
    this.inventory = new Map();
    this.reservations = new Map();
  }

  /**
   * Get all inventory with product details
   */
  async getAllInventory() {
    const inventory = Array.from(this.inventory.values());
    
    // Enrich with product data (circular dependency)
    const enriched = await Promise.all(
      inventory.map(async (item) => {
        const product = await ProductService.getProductById(item.productId);
        const pendingOrders = await OrderService.getPendingOrdersForProduct(item.productId);
        
        return {
          ...item,
          productDetails: product,
          pendingOrderCount: pendingOrders.length,
          availableStock: item.quantity - (this.reservations.get(item.productId) || 0),
        };
      })
    );
    
    return enriched;
  }

  /**
   * Get stock level for a product
   */
  async getStockLevel(productId) {
    const stock = this.inventory.get(productId);
    if (!stock) {
      return {
        productId,
        quantity: 0,
        reserved: 0,
        available: 0,
        status: 'out_of_stock',
      };
    }

    const reserved = this.reservations.get(productId) || 0;
    const available = stock.quantity - reserved;

    return {
      productId,
      quantity: stock.quantity,
      reserved,
      available,
      status: this.getStockStatus(available),
      lastUpdated: stock.lastUpdated,
    };
  }

  /**
   * Determine stock status
   */
  getStockStatus(available) {
    if (available === 0) return 'out_of_stock';
    if (available < 10) return 'low_stock';
    if (available < 50) return 'medium_stock';
    return 'in_stock';
  }

  /**
   * Initialize stock for a new product
   */
  async initializeStock(productId, quantity) {
    const stock = {
      productId,
      quantity,
      lastUpdated: new Date().toISOString(),
    };

    this.inventory.set(productId, stock);
    this.reservations.set(productId, 0);

    return stock;
  }

  /**
   * Update stock quantity
   */
  async updateStock(productId, quantity) {
    const stock = this.inventory.get(productId);
    if (!stock) {
      throw new Error('Product not found in inventory');
    }

    const updated = {
      ...stock,
      quantity,
      lastUpdated: new Date().toISOString(),
    };

    this.inventory.set(productId, updated);

    // Check if product needs reordering
    const product = await ProductService.getProductById(productId);
    if (quantity < 10) {
      console.warn(`Low stock alert for ${product.name}: ${quantity} units remaining`);
    }

    return updated;
  }

  /**
   * Add stock (restock)
   */
  async addStock(productId, quantity) {
    const stock = this.inventory.get(productId);
    if (!stock) {
      return this.initializeStock(productId, quantity);
    }

    return this.updateStock(productId, stock.quantity + quantity);
  }

  /**
   * Reserve stock for an order
   */
  async reserveStock(productId, quantity) {
    const stock = await this.getStockLevel(productId);
    
    if (stock.available < quantity) {
      throw new Error(`Insufficient stock to reserve ${quantity} units`);
    }

    const currentReserved = this.reservations.get(productId) || 0;
    this.reservations.set(productId, currentReserved + quantity);

    return {
      productId,
      reserved: quantity,
      totalReserved: currentReserved + quantity,
    };
  }

  /**
   * Release reserved stock (when order is cancelled)
   */
  async releaseReservedStock(productId, quantity) {
    const currentReserved = this.reservations.get(productId) || 0;
    const newReserved = Math.max(0, currentReserved - quantity);
    
    this.reservations.set(productId, newReserved);

    return {
      productId,
      released: quantity,
      totalReserved: newReserved,
    };
  }

  /**
   * Deduct stock (when order is completed)
   */
  async deductStock(productId, quantity) {
    const stock = this.inventory.get(productId);
    if (!stock) {
      throw new Error('Product not found in inventory');
    }

    // Release reservation
    await this.releaseReservedStock(productId, quantity);

    // Deduct from actual stock
    const newQuantity = Math.max(0, stock.quantity - quantity);
    await this.updateStock(productId, newQuantity);

    // Check if reorder is needed
    if (newQuantity < 10) {
      const product = await ProductService.getProductById(productId);
      console.warn(`Reorder needed for ${product.name}: ${newQuantity} units remaining`);
    }

    return {
      productId,
      deducted: quantity,
      newQuantity,
    };
  }

  /**
   * Remove product from inventory
   */
  async removeProduct(productId) {
    // Check for reserved stock
    const reserved = this.reservations.get(productId) || 0;
    if (reserved > 0) {
      throw new Error('Cannot remove product with reserved stock');
    }

    this.inventory.delete(productId);
    this.reservations.delete(productId);

    return true;
  }

  /**
   * Get low stock products
   */
  async getLowStockProducts(threshold = 10) {
    const lowStock = [];

    for (const [productId, stock] of this.inventory.entries()) {
      const reserved = this.reservations.get(productId) || 0;
      const available = stock.quantity - reserved;

      if (available < threshold) {
        const product = await ProductService.getProductById(productId);
        lowStock.push({
          productId,
          productName: product.name,
          quantity: stock.quantity,
          reserved,
          available,
          status: this.getStockStatus(available),
        });
      }
    }

    return lowStock;
  }

  /**
   * Get inventory statistics
   */
  async getInventoryStatistics() {
    const inventory = Array.from(this.inventory.values());
    
    const stats = {
      totalProducts: inventory.length,
      totalUnits: inventory.reduce((sum, item) => sum + item.quantity, 0),
      totalReserved: Array.from(this.reservations.values()).reduce((sum, r) => sum + r, 0),
      lowStockCount: (await this.getLowStockProducts()).length,
      outOfStockCount: inventory.filter((item) => item.quantity === 0).length,
    };

    return stats;
  }

  /**
   * Bulk update inventory
   */
  async bulkUpdateInventory(updates) {
    const results = [];

    for (const update of updates) {
      try {
        const result = await this.updateStock(update.productId, update.quantity);
        results.push({ success: true, ...result });
      } catch (error) {
        results.push({
          success: false,
          productId: update.productId,
          error: error.message,
        });
      }
    }

    return results;
  }
}

module.exports = new InventoryService();

// Made with Bob
