# Galaxy Store API - Demo Project

**⚠️ This is a deliberately broken demo project for testing ZeroLoop scanner**

## Purpose

This project demonstrates a realistic e-commerce backend with **intentionally planted issues** to showcase ZeroLoop's detection capabilities.

## Planted Issues

### 1. **Dependency Conflicts**
- ✗ Express 4.18.2 with body-parser 1.19.0 (redundant)
- ✗ Mongoose 5.13.15 with MongoDB driver 4.0.0 (incompatible)
- ✗ Winston + Bunyan + Morgan all installed (multiple loggers)

### 2. **Node Version Mismatch**
- ✗ package.json requires Node >=18.0.0
- ✗ .nvmrc specifies Node 14.21.3
- ✗ Creates deployment confusion

### 3. **Circular Dependencies**
- ✗ ProductService → OrderService → InventoryService → ProductService
- ✗ Each service imports the other two
- ✗ Creates tight coupling and potential runtime issues

## Project Structure

```
scanner/test_project/
├── package.json              # Conflicting dependencies
├── .nvmrc                    # Mismatched Node version
├── index.js                  # Main server using all conflicts
└── services/
    ├── ProductService.js     # Imports Order + Inventory
    ├── OrderService.js       # Imports Product + Inventory
    └── InventoryService.js   # Imports Product + Order
```

## What ZeroLoop Should Detect

When you run ZeroLoop on this project, it should find:

1. **BLOCKED Status** - Critical issues prevent safe development
2. **6 Total Issues**:
   - 1 Incompatibility (Mongoose/MongoDB)
   - 2 Conflicts (Multiple loggers, Node version mismatch)
   - 1 Redundancy (body-parser)
   - 1 Warning (Current Node version)
   - 1 Info (Circular deps check)

3. **Estimated Savings**: ~25-30 Bobcoins from preventing retry loops

## How to Test

### Using ZeroLoop Scanner:
```bash
# From project root
python scanner/analyze.py scanner/test_project
```

### Using ZeroLoop Web UI:
1. Start Next.js: `npm run dev`
2. Open http://localhost:3000
3. Enter path: `scanner/test_project`
4. Click "Run ZeroLoop"
5. View results with clearance status

### Using API:
```bash
curl -X POST http://localhost:3000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"projectPath": "scanner/test_project"}'
```

## Expected Bob Context

ZeroLoop should generate a context prompt warning Bob about:

- **DO NOT** use `bodyParser.json()` - use `express.json()` instead
- **DO NOT** attempt MongoDB connection until versions are compatible
- **DO NOT** add logging without checking which logger is standard
- **DO NOT** install packages until Node versions are aligned

## Realistic Elements

This isn't a toy project - it includes:

✓ **Real API Structure**: Express server with routes
✓ **Proper Middleware**: CORS, Helmet, Compression
✓ **Service Layer**: Product, Order, Inventory services
✓ **Error Handling**: Try-catch blocks, error middleware
✓ **Logging**: Multiple loggers (intentionally conflicting)
✓ **Database**: Mongoose models and connections
✓ **Business Logic**: Stock management, order processing

## What Makes It Broken

1. **body-parser Import**: Lines 7 in index.js - redundant with Express 4.18+
2. **Multiple Loggers**: Lines 15-17 in index.js - winston, bunyan, morgan all used
3. **Mongoose Version**: package.json line 32 - incompatible with MongoDB driver
4. **Node Mismatch**: package.json engines vs .nvmrc - deployment confusion
5. **Circular Imports**: Services all import each other - tight coupling

## How to Fix (For Demo Purposes)

**Don't fix these issues!** They're intentional for testing ZeroLoop.

But if you wanted to fix them:

1. Remove body-parser, use express.json()
2. Upgrade Mongoose to 6.x or 7.x
3. Pick one logger (winston recommended)
4. Align Node versions (use 18.x)
5. Break circular dependencies with dependency injection

## License

MIT - This is a demo project for ZeroLoop testing