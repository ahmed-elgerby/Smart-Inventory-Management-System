# System Analysis and Requirement Design

## 1. Introduction

### 1.1 Purpose
This document outlines the system analysis and requirement design for the Smart Inventory Management System. The system is designed to provide inventory tracking, automated alerting for stock levels, and comprehensive reporting capabilities across multiple warehouses for our company.

### 1.2 Scope
The system encompasses:
- User management with role-based access control
- Multi-warehouse inventory management
- Real-time stock level monitoring and alerting
- Comprehensive reporting and analytics
- RESTful API interfaces for all services

### 1.3 System Overview
The Smart Inventory Management System is a microservices-based application that supports inventory operations across 10 warehouses with up to 122 concurrent users. The system provides automated alerts for low stock conditions and generates detailed reports for inventory analysis.

## 2. Functional Requirements

### 2.1 User Management
- **1**: User registration and authentication with JWT tokens
- **2**: Role-based access control (Admin, Manager, Employee)
- **3**: User profile management

### 2.2 Inventory Management
- **1**: CRUD operations for inventory items
- **2**: Multi-warehouse stock tracking via item_locations table
- **3**: Item categorization and pricing
- **4**: Image upload for item pictures
- **5**: SKU-based item identification

### 2.3 Location Management
- **1**: Warehouse/location creation and management
- **2**: Location-based inventory distribution
- **3**: Address management for locations

### 2.4 Alerting Microservice
- **1**: Automatic low stock alerts when quantity < min_quantity
- **2**: Automatic out-of-stock alerts when quantity = 0
- **3**: Real-time alert generation on inventory changes

### 2.5 Reporting Microservice
- **1**: Inventory summary reports with totals and aggregations
- **2**: Category-based inventory analysis
- **3**: Top 10 items by value reporting
- **4**: Low stock and out-of-stock item listings
- **5**: Activity log reporting with user actions

### 2.6 Activity Logging
- **1**: Comprehensive audit trail for all user actions
- **2**: Action details storage and retrieval
- **3**: User activity monitoring

## 3. Non-Functional Requirements

### 3.1 Performance
- **1**: Support for 122 concurrent users
- **2**: Database queries optimized for 5,000 items per warehouse
- **3**: Horizontal scaling capability for microservices

### 3.2 Scalability
- **1**: Microservices architecture for independent scaling
- **2**: Kubernetes deployment with pod replication


## 4. System Architecture

### 4.1 High-Level Architecture
The system follows a microservices architecture with the following components:
- **Frontend Service**: Nginx-served static web application
- **Backend Service**: Main Flask application handling business logic
- **Alert Service**: Dedicated service for alert management
- **Reporting Service**: Dedicated service for report generation
- **Database**: PostgreSQL database with normalized schema and initial data for our trials

### 4.2 Database Design
- **Users Table**: User information with role-based access
- **Items Table**: Core inventory items with metadata
- **Item_Locations Table**: Multi-warehouse stock distribution
- **Locations Table**: Warehouse/location information
- **Alerts Table**: Alert tracking and status management
- **Activity_Log Table**: Audit trail for user actions


## 5. Testing Use Cases

### 5.1 Primary Use Cases
1. **User Authentication**: Users log in with credentials and receive JWT tokens
2. **Inventory CRUD**: Managers and admins create, read, update, and delete inventory items
3. **Stock Management**: Employees update stock levels across multiple warehouses
4. **Alert Monitoring**: Users view active alerts and resolve them
5. **Report Generation**: Managers access various inventory reports
6. **Location Management**: Admins manage warehouse locations

### 5.2 Secondary Use Cases
1. **User Profile Management**: Users update their profiles and upload photos
2. **Activity Monitoring**: Admins review user activity logs
3. **Category Analysis**: Managers analyze inventory by categories
4. **Low Stock Alerts**: System automatically generates alerts for stock issues

## 6. Constraints and Assumptions

### 6.1 Technical Constraints
- Containerized deployment using Docker
- Kubernetes orchestration for production
- PostgreSQL as the database system
- Python Flask for backend services

### 6.2 Business Constraints
- Support for 10 warehouses with 122 total users
- Up to 5,000 unique items per warehouse
- Real-time alerting requirements
- Multi-warehouse inventory distribution

### 6.3 Assumptions
- Users have basic computer literacy
- Network connectivity is reliable
- Database size remains within estimated limits (80-95MB)