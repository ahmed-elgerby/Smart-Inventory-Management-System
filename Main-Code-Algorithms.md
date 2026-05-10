# Algorithms, Methods, and Techniques Used

## 1. Overview

This document describes the key algorithms, methods, and techniques implemented in the Smart Inventory Management System. The system employs various computational approaches for inventory management, alerting, reporting, and security.

## 2. Authentication and Authorization Algorithms

### 2.1 JWT Token Generation and Validation
- **Algorithm**: JSON Web Token (JWT) with HS256 hashing algorithm
- **Method**: Stateless authentication using digitally signed tokens
- **Technique**: Token contains user ID, role, and location information
- **Security**: 24-hour token expiry with server-side secret key validation
- **Implementation**: Uses PyJWT library for encoding/decoding operations

### 2.2 Password Hashing
- **Algorithm**: PBKDF2 with SHA-256 (default Werkzeug implementation)
- **Method**: One-way password hashing with salt
- **Technique**: Secure password storage preventing plaintext recovery
- **Implementation**: werkzeug.security.generate_password_hash() and check_password_hash()

### 2.3 Role-Based Access Control (RBAC)
- **Algorithm**: Hierarchical permission checking
- **Method**: Decorator-based authorization middleware
- **Technique**: Admin > Manager > Employee permission hierarchy
- **Implementation**: Flask route decorators checking user roles from JWT payload

## 3. Inventory Management Algorithms

### 3.1 Multi-Warehouse Stock Distribution
- **Algorithm**: Normalized relational mapping
- **Method**: Item-to-location many-to-many relationship via junction table
- **Technique**: item_locations table with UNIQUE constraint on (item_id, location_id)
- **Implementation**: Separate quantity tracking per warehouse location

### 3.2 Stock Level Validation
- **Algorithm**: Threshold-based validation
- **Method**: Pre-update checks for quantity constraints
- **Technique**: Ensures quantity >= 0 and min_quantity >= 0
- **Implementation**: Database-level CHECK constraints and application validation

### 3.3 SKU Generation and Validation
- **Algorithm**: Unique identifier generation
- **Method**: User-provided or auto-generated SKU codes
- **Technique**: Database UNIQUE constraint enforcement
- **Implementation**: PostgreSQL unique indexes for SKU validation

## 4. Alerting System Algorithms

### 4.1 Threshold-Based Alert Generation
- **Algorithm**: Rule-based decision tree for stock status
- **Method**: Conditional logic based on quantity vs min_quantity comparison
- **Technique**:
  ```
  IF quantity == 0:
      Create "out_of_stock" alert
      Resolve any existing "low_stock" alert
  ELIF quantity < min_quantity:
      Create "low_stock" alert
      Resolve any existing "out_of_stock" alert
  ELSE:
      Resolve all active alerts for the item
  ```
- **Implementation**: check_and_create_alerts_for_item() function

### 4.2 Alert Deduplication
- **Algorithm**: Existence checking before alert creation
- **Method**: Query existing active alerts for the item
- **Technique**: Prevents duplicate alerts of the same type
- **Implementation**: SELECT query checking alert_type in existing_alerts list

### 4.3 Alert Prioritization
- **Algorithm**: Weighted ordering for display
- **Method**: CASE statement in SQL ORDER BY clause
- **Technique**: out_of_stock (priority 1) > low_stock (priority 2) > others (priority 3)
- **Implementation**: Database query with conditional ordering

## 5. Reporting Algorithms

### 5.1 Inventory Aggregation
- **Algorithm**: SQL aggregation functions with COALESCE for null handling
- **Method**: SUM, COUNT, CASE statements for conditional counting
- **Technique**:
  - Total items: COUNT(*)
  - Total quantity: COALESCE(SUM(quantity), 0)
  - Total value: COALESCE(SUM(price * quantity), 0)
  - Stock status counts using conditional CASE statements
- **Implementation**: Single query with multiple aggregation calculations

### 5.2 Category-Based Analysis
- **Algorithm**: GROUP BY aggregation with filtering
- **Method**: Category-wise grouping with NULL exclusion
- **Technique**: GROUP BY category ORDER BY total_value DESC
- **Implementation**: SQL GROUP BY with aggregate functions per category

### 5.3 Top-N Items Ranking
- **Algorithm**: Value-based sorting with LIMIT
- **Method**: Calculated total_value = quantity * price
- **Technique**: ORDER BY (quantity * price) DESC LIMIT 10
- **Implementation**: SQL ORDER BY with computed column

### 5.4 Low Stock Analysis
- **Algorithm**: Deficit calculation and prioritization
- **Method**: needed = min_quantity - quantity
- **Technique**: WHERE quantity < min_quantity ORDER BY needed DESC
- **Implementation**: SQL computed column with conditional filtering

## 6. Activity Logging Techniques

### 6.1 Audit Trail Implementation
- **Algorithm**: Event-driven logging
- **Method**: Database triggers and application-level logging
- **Technique**: Automatic timestamping with user_id association
- **Implementation**: INSERT operations on activity_log table

### 6.2 Action Detail Parsing
- **Algorithm**: String pattern matching for item name extraction
- **Method**: Regular expression parsing of action details
- **Technique**: Extract item names from log messages for reporting
- **Implementation**: Python re module for pattern matching

## 7. Database Optimization Techniques

### 7.1 Connection Pooling
- **Algorithm**: Connection reuse pattern
- **Method**: psycopg2 connection management
- **Technique**: Get connection, execute queries, close connection
- **Implementation**: get_db() function returning fresh connections

### 7.2 Query Optimization
- **Algorithm**: Indexed retrieval with JOIN optimization
- **Method**: Proper indexing on foreign keys and frequently queried columns
- **Technique**: LEFT JOIN for optional relationships, cursor_factory for dict results
- **Implementation**: psycopg2.extras.RealDictCursor for object-like access

### 7.3 Transaction Management
- **Algorithm**: ACID transaction handling
- **Method**: Explicit commit/rollback based on operation success
- **Technique**: Try/except blocks with conn.commit() and conn.rollback()
- **Implementation**: Database transaction wrapping for multi-statement operations

## 8. File Upload and Storage Techniques

### 8.1 Image Handling
- **Algorithm**: Binary data storage in database
- **Method**: BYTEA column storage with filename metadata
- **Technique**: Base64 encoding for JSON transmission, file size limits
- **Implementation**: Flask file upload handling with werkzeug FileStorage

### 8.2 File Validation
- **Algorithm**: Extension and size checking
- **Method**: Server-side validation before storage
- **Technique**: Allowed extensions, maximum file size (5MB)
- **Implementation**: Flask configuration and request validation

## 9. Error Handling and Resilience Techniques

### 9.1 Exception Management
- **Algorithm**: Try/catch with specific error types
- **Method**: psycopg2.IntegrityError handling for constraint violations
- **Technique**: Rollback on errors, appropriate HTTP status codes
- **Implementation**: Python try/except blocks with database rollback

### 9.2 Graceful Degradation
- **Algorithm**: Fallback mechanisms for service failures
- **Method**: Import error handling for optional dependencies
- **Technique**: Default function implementations when modules unavailable
- **Implementation**: try/except imports with fallback functions

## 10. Deployment and Scaling Techniques

### 10.1 Containerization
- **Algorithm**: Docker image layering
- **Method**: Multi-stage builds for optimization
- **Technique**: Python virtual environment, minimal base images
- **Implementation**: Dockerfile with requirements.txt installation

### 10.2 Orchestration
- **Algorithm**: Kubernetes pod scheduling
- **Method**: Replica sets for high availability
- **Technique**: Service discovery, load balancing
- **Implementation**: Kubernetes manifests with deployment configurations

### 10.3 CI/CD Pipeline
- **Algorithm**: Automated build and deployment
- **Method**: Jenkins pipeline with stages
- **Technique**: Docker image building, Kubernetes deployment
- **Implementation**: Jenkinsfile with scripted pipeline syntax

## 11. Performance Optimization Techniques

### 11.1 Database Indexing
- **Algorithm**: B-tree indexing for query optimization
- **Method**: Primary keys, foreign keys, unique constraints
- **Technique**: Automatic index creation on constrained columns
- **Implementation**: PostgreSQL automatic indexing

### 11.2 Query Result Limiting
- **Algorithm**: Pagination and result set limiting
- **Method**: LIMIT clauses for large result sets
- **Technique**: Top-N queries for performance
- **Implementation**: SQL LIMIT with ORDER BY

### 11.3 Caching Strategies
- **Algorithm**: In-memory result caching (future enhancement)
- **Method**: Redis or application-level caching
- **Technique**: Cache frequently accessed data like user permissions
