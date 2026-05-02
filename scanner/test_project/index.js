/**
 * Galaxy Store API - Main Server
 * E-commerce backend for product catalog, orders, and inventory management
 */

require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser'); // Redundant with Express 4.18+
const mongoose = require('mongoose');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');

// Multiple logging libraries (conflict)
const winston = require('winston');
const bunyan = require('bunyan');
const morgan = require('morgan');

// Services with circular dependencies
const ProductService = require('./services/ProductService');
const OrderService = require('./services/OrderService');
const InventoryService = require('./services/InventoryService');

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Configure Winston logger
const winstonLogger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' }),
  ],
});

// Configure Bunyan logger
const bunyanLogger = bunyan.createLogger({
  name: 'galaxy-store-api',
  streams: [
    {
      level: 'info',
      stream: process.stdout,
    },
  ],
});

// Middleware
app.use(helmet());
app.use(compression());
app.use(cors());
app.use(morgan('combined')); // HTTP request logging
app.use(bodyParser.json()); // Should use express.json() instead
app.use(bodyParser.urlencoded({ extended: true })); // Should use express.urlencoded()

// MongoDB Connection
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/galaxy-store';

mongoose
  .connect(MONGODB_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
  })
  .then(() => {
    winstonLogger.info('Connected to MongoDB');
    bunyanLogger.info('MongoDB connection established');
    console.log('✓ Database connected');
  })
  .catch((error) => {
    winstonLogger.error('MongoDB connection error:', error);
    bunyanLogger.error({ err: error }, 'Failed to connect to MongoDB');
    console.error('✗ Database connection failed:', error.message);
    process.exit(1);
  });

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: process.env.NODE_ENV || 'development',
  });
});

// API Routes

// Products
app.get('/api/products', async (req, res) => {
  try {
    const products = await ProductService.getAllProducts();
    winstonLogger.info('Retrieved all products');
    res.json({ success: true, data: products });
  } catch (error) {
    bunyanLogger.error({ err: error }, 'Failed to retrieve products');
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/products/:id', async (req, res) => {
  try {
    const product = await ProductService.getProductById(req.params.id);
    if (!product) {
      return res.status(404).json({ success: false, error: 'Product not found' });
    }
    res.json({ success: true, data: product });
  } catch (error) {
    winstonLogger.error('Product retrieval error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/products', async (req, res) => {
  try {
    const product = await ProductService.createProduct(req.body);
    bunyanLogger.info({ productId: product.id }, 'Product created');
    res.status(201).json({ success: true, data: product });
  } catch (error) {
    winstonLogger.error('Product creation error:', error);
    res.status(400).json({ success: false, error: error.message });
  }
});

// Orders
app.get('/api/orders', async (req, res) => {
  try {
    const orders = await OrderService.getAllOrders();
    res.json({ success: true, data: orders });
  } catch (error) {
    bunyanLogger.error({ err: error }, 'Failed to retrieve orders');
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/orders', async (req, res) => {
  try {
    const order = await OrderService.createOrder(req.body);
    winstonLogger.info(`Order created: ${order.id}`);
    bunyanLogger.info({ orderId: order.id }, 'New order placed');
    res.status(201).json({ success: true, data: order });
  } catch (error) {
    winstonLogger.error('Order creation error:', error);
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/orders/:id', async (req, res) => {
  try {
    const order = await OrderService.getOrderById(req.params.id);
    if (!order) {
      return res.status(404).json({ success: false, error: 'Order not found' });
    }
    res.json({ success: true, data: order });
  } catch (error) {
    bunyanLogger.error({ err: error }, 'Order retrieval failed');
    res.status(500).json({ success: false, error: error.message });
  }
});

// Inventory
app.get('/api/inventory', async (req, res) => {
  try {
    const inventory = await InventoryService.getAllInventory();
    res.json({ success: true, data: inventory });
  } catch (error) {
    winstonLogger.error('Inventory retrieval error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/inventory/:productId', async (req, res) => {
  try {
    const stock = await InventoryService.getStockLevel(req.params.productId);
    res.json({ success: true, data: stock });
  } catch (error) {
    bunyanLogger.error({ err: error }, 'Stock level check failed');
    res.status(500).json({ success: false, error: error.message });
  }
});

app.put('/api/inventory/:productId', async (req, res) => {
  try {
    const updated = await InventoryService.updateStock(req.params.productId, req.body.quantity);
    winstonLogger.info(`Inventory updated for product ${req.params.productId}`);
    res.json({ success: true, data: updated });
  } catch (error) {
    bunyanLogger.error({ err: error }, 'Inventory update failed');
    res.status(400).json({ success: false, error: error.message });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  winstonLogger.error('Unhandled error:', err);
  bunyanLogger.error({ err }, 'Unhandled error occurred');
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined,
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: 'Endpoint not found',
    path: req.path,
  });
});

// Start server
app.listen(PORT, () => {
  winstonLogger.info(`Galaxy Store API running on port ${PORT}`);
  bunyanLogger.info({ port: PORT }, 'Server started');
  console.log(`🚀 Galaxy Store API listening on port ${PORT}`);
  console.log(`📦 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 Health check: http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  winstonLogger.info('SIGTERM received, shutting down gracefully');
  bunyanLogger.info('Graceful shutdown initiated');
  mongoose.connection.close(() => {
    console.log('MongoDB connection closed');
    process.exit(0);
  });
});

module.exports = app;

// Made with Bob
