# Smart-Inventory-Management-System

## Project Overview
Develop a real-time inventory tracking system that generates alerts for low stock and produces reports. The project focuses on DevOps practices: containerizing microservices, implementing CI/CD pipelines, deploying on Kubernetes, and automating infrastructure with Terraform and Ansible. No AI components are required. This is part of the DevOps course in the Digital Egypt Pioneers initiative (DEPI).

## Design Assumptions
The following assumptions was used for the system K8S design, scaling, and resource estimates:

- **User Base**: The system supports 122 users across 10 warehouses. Each warehouse has 10 employees, 1 manager, and 1 IT member (10 × 12 = 120). Additional access for the company CEO and IT Manager brings the total to 122. All users may access the system simultaneously, requiring concurrent handling and load balancing.

- **Inventory Scale**: Up to 5,000 unique items per warehouse, with variable quantities. Items can be distributed across multiple locations (warehouses), with an average of 2 locations per item.

- **Database Structure and Size**:
  - **Tables and Rows**:
    - Users: 122 rows (50% have profile photos averaging 10KB each; text fields average half their max length).
    - Items: 5,000 rows (50% have product pictures averaging 20KB each; text fields average half their max length).
    - Item Locations: 10,000 rows (based on 2 average locations per item).
    - Alerts: 500 rows (10% of items trigger alerts for low/out-of-stock).
    - Activity Log: 1,220 rows (10 actions logged per user).
    - Locations: 3 rows (minimal, as in seed data).
  - **Estimated Table Sizes**:
    - Users: ~667 KB (dominated by photos).
    - Items: ~52.7 MB (large due to pictures and volume).
    - Item Locations: ~240 KB (small rows, many entries).
    - Alerts: ~129 KB (moderate text content).
    - Activity Log: ~750 KB (text-heavy details).
    - Locations: ~1 KB (negligible).
  - **Total Database Size**: ~80-95 MB (includes raw data ~54.5 MB, indexes ~20-30 MB, and overhead ~5-10 MB like PostgreSQL WAL and system tables).

- **Concurrency and Performance**: Designed for 122 simultaneous users, with stateless services scaled horizontally. Database queries assume moderate load; no extreme optimizations needed for this scale.

## Pod Estimation
- **HA Strategy**: Every service is planned with at least one replica on a second node, so the cluster can tolerate a node failure without losing availability.
- **Database**: 1 pod for PostgreSQL, with a stand-by replica on another node for high availability.
- **Frontend**: 2 pods, replicated across the two nodes to ensure HA, failover and load distribution.
- **Backend**: 2 pods, replicated across the two nodes to ensure HA, failover and load distribution.
- **Microservices**: 1 pod each for Alert Service and Reporting Service, with each service replicated onto another node for availability.


