resource "aws_key_pair" "deployer" {
  key_name   = "smart-inventory-key"
  public_key = tls_private_key.deployer.public_key_openssh
}

resource "local_file" "ssh_key" {
  filename        = "${path.module}/smart-inventory-key.pem"
  content         = tls_private_key.deployer.private_key_pem
  file_permission = "0400"
}

resource "tls_private_key" "deployer" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# --- DATA SOURCES FOR EXISTING RESOURCES ---

data "aws_security_groups" "existing_inventory_sg" {
  filter {
    name   = "group-name"
    values = ["inventory-sg"]
  }
}

data "aws_security_groups" "existing_alb_sg" {
  filter {
    name   = "group-name"
    values = ["inventory-alb-sg"]
  }
}

data "aws_instances" "existing_controller" {
  filter {
    name   = "tag:Name"
    values = ["Smart-Inventory-controller"]
  }
}

data "aws_instances" "existing_worker" {
  filter {
    name   = "tag:Name"
    values = ["Smart-Inventory-worker"]
  }
}

data "aws_instance" "controller" {
  count       = length(data.aws_instances.existing_controller.ids) > 0 ? 1 : 0
  instance_id = data.aws_instances.existing_controller.ids[0]
}

data "aws_instance" "worker" {
  count       = length(data.aws_instances.existing_worker.ids) > 0 ? 1 : 0
  instance_id = data.aws_instances.existing_worker.ids[0]
}

# --- LOCALS ---

locals {
  inventory_sg_id = length(data.aws_security_groups.existing_inventory_sg.ids) > 0 ? data.aws_security_groups.existing_inventory_sg.ids[0] : aws_security_group.inventory_sg.id
  alb_sg_id       = length(data.aws_security_groups.existing_alb_sg.ids) > 0 ? data.aws_security_groups.existing_alb_sg.ids[0] : aws_security_group.alb_sg.id
  create_sg       = length(data.aws_security_groups.existing_inventory_sg.ids) == 0
  create_alb_sg   = length(data.aws_security_groups.existing_alb_sg.ids) == 0

  instances_to_create = {
    controller = length(data.aws_instances.existing_controller.ids) == 0
    worker     = length(data.aws_instances.existing_worker.ids) == 0
  }
  instance_keys = [for k, v in local.instances_to_create : k if v]

  controller_public_ip = length(data.aws_instances.existing_controller.ids) > 0 ? data.aws_instance.controller[0].public_ip : aws_instance.instances["controller"].public_ip
  worker_public_ip     = length(data.aws_instances.existing_worker.ids) > 0 ? data.aws_instance.worker[0].public_ip : aws_instance.instances["worker"].public_ip
  controller_id        = length(data.aws_instances.existing_controller.ids) > 0 ? data.aws_instance.controller[0].id : aws_instance.instances["controller"].id
  worker_id            = length(data.aws_instances.existing_worker.ids) > 0 ? data.aws_instance.worker[0].id : aws_instance.instances["worker"].id
  controller_host_name = length(data.aws_instances.existing_controller.ids) > 0 ? "controller-node-existing" : "controller-node"
  worker_host_name     = length(data.aws_instances.existing_worker.ids) > 0 ? "worker-node-existing" : "worker-node"
}

# --- SECURITY GROUPS ---

resource "aws_security_group" "inventory_sg" {
  name        = "inventory-sg"
  description = "Internal and management traffic for K8s nodes"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # THE FIX: Allow ALL internal traffic between nodes (Kubelet, Etcd, Flannel)
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  # Allow the ALB to reach the NodePort
  ingress {
    from_port       = 30080
    to_port         = 30080
    protocol        = "tcp"
    security_groups = [local.alb_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "alb_sg" {
  name        = "inventory-alb-sg"
  description = "Public web traffic for ALB"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- EC2 INSTANCES ---

resource "aws_instance" "instances" {
  for_each = toset(local.instance_keys)

  ami                         = "ami-0c7217cdde317cfec"
  instance_type               = "t3.small"
  vpc_security_group_ids      = [local.inventory_sg_id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.deployer.key_name
  availability_zone           = each.key == "controller" ? "us-east-1a" : "us-east-1b"

  tags = {
    Name = "Smart-Inventory-${each.key}"
  }
}


# --- DATA SOURCES FOR ALB ---

data "aws_vpc" "default" {
  default = true
}

# Fix: Dynamically find subnets that match the AZs of your instances
data "aws_subnets" "available" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = ["us-east-1a", "us-east-1b"]
  }
}

# --- LOAD BALANCER ---

resource "aws_lb" "inventory_alb" {
  name               = "smart-inventory-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [local.alb_sg_id]
  subnets            = data.aws_subnets.available.ids

  enable_deletion_protection = false
}

resource "aws_lb_target_group" "inventory_tg" {
  name        = "smart-inventory-tg"
  port        = 30080
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "instance"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    interval            = 30
    path                = "/"
    port                = "30080"
    matcher             = "200-399"
  }
}

output "aws_lb_inventory_alb_dns_name" {
  value = aws_lb.inventory_alb.dns_name
}

resource "aws_lb_target_group_attachment" "inventory_controller" {
  target_group_arn = aws_lb_target_group.inventory_tg.arn
  target_id        = local.controller_id
  port             = 30080
}

resource "aws_lb_target_group_attachment" "inventory_worker" {
  target_group_arn = aws_lb_target_group.inventory_tg.arn
  target_id        = local.worker_id
  port             = 30080
}

resource "aws_lb_listener" "inventory_http" {
  load_balancer_arn = aws_lb.inventory_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.inventory_tg.arn
  }
}

# --- OUTPUTS ---

output "controller_ip" {
  value = local.controller_public_ip
}

output "worker_ip" {
  value = local.worker_public_ip
}

output "alb_dns_name" {
  value = aws_lb.inventory_alb.dns_name
}

resource "local_file" "ansible_inventory" {
  filename        = "${path.module}/hosts.ini"
  file_permission = "0644"
  content = <<-EOT
    [controller]
    ${local.controller_host_name} ansible_host=${local.controller_public_ip} ansible_user=ubuntu ansible_ssh_private_key_file=${path.module}/smart-inventory-key.pem

    [worker]
    ${local.worker_host_name} ansible_host=${local.worker_public_ip} ansible_user=ubuntu ansible_ssh_private_key_file=${path.module}/smart-inventory-key.pem
    EOT
}
