/**
 * Product Service
 * Handles product catalog operations
 */

const OrderService = require('./OrderService');
const InventoryService = require('./InventoryService');

class ProductService {
  constructor() {
    this.products = new Map();
  }

  /**
   * Get all products with inventory and order statistics
   */
  async getAllProducts() {
    const products = Array.from(this.products.values());
    
    // Enrich products with inventory data (circular dependency)
    const enriched = await Promise.all(
      products.map(async (product) => {
        const stock = await InventoryService.getStockLevel(product.id);
        const orderCount = await OrderService.getOrderCountForProduct(product.id);
        
        return {
          ...product,
          stockLevel: stock,
          totalOrders: orderCount,
        };
      })
    );
    
    return enriched;
  }

  /**
   * Get product by ID
   */
  async getProductById(productId) {
    const product = this.products.get(productId);
    if (!product) {
      return null;
    }

    // Get related data from other services
    const stock = await InventoryService.getStockLevel(productId);
    const recentOrders = await OrderService.getRecentOrdersForProduct(productId);

    return {
      ...product,
      stockLevel: stock,
      recentOrders,
    };
  }

  /**
   * Create new product
   */
  async createProduct(productData) {
    const product = {
      id: `prod_${Date.now()}`,
      name: productData.name,
      description: productData.description,
      price: productData.price,
      category: productData.category,
      createdAt: new Date().toISOString(),
    };

    this.products.set(product.id, product);

    // Initialize inventory for new product
    await InventoryService.initializeStock(product.id, productData.initialStock || 0);

    return product;
  }

  /**
   * Update product details
   */
  async updateProduct(productId, updates) {
    const product = this.products.get(productId);
    if (!product) {
      throw new Error('Product not found');
    }

    const updated = {
      ...product,
      ...updates,
      updatedAt: new Date().toISOString(),
    };

    this.products.set(productId, updated);
    return updated;
  }

  /**
   * Delete product
   */
  async deleteProduct(productId) {
    // Check if product has pending orders
    const pendingOrders = await OrderService.getPendingOrdersForProduct(productId);
    if (pendingOrders.length > 0) {
      throw new Error('Cannot delete product with pending orders');
    }

    // Remove from inventory
    await InventoryService.removeProduct(productId);

    return this.products.delete(productId);
  }

  /**
   * Get products by category
   */
  async getProductsByCategory(category) {
    const products = Array.from(this.products.values()).filter(
      (p) => p.category === category
    );

    // Enrich with inventory data
    return Promise.all(
      products.map(async (product) => ({
        ...product,
        stockLevel: await InventoryService.getStockLevel(product.id),
      }))
    );
  }

  /**
   * Search products
   */
  async searchProducts(query) {
    const products = Array.from(this.products.values()).filter(
      (p) =>
        p.name.toLowerCase().includes(query.toLowerCase()) ||
        p.description.toLowerCase().includes(query.toLowerCase())
    );

    return products;
  }

  /**
   * Get low stock products
   */
  async getLowStockProducts(threshold = 10) {
    const products = Array.from(this.products.values());
    const lowStock = [];

    for (const product of products) {
      const stock = await InventoryService.getStockLevel(product.id);
      if (stock.quantity < threshold) {
        lowStock.push({
          ...product,
          stockLevel: stock,
        });
      }
    }

    return lowStock;
  }
}

module.exports = new ProductService();

// Made with Bob
