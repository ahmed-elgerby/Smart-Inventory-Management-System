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

data "aws_lbs" "existing_alb" {
  filter {
    name   = "name"
    values = ["smart-inventory-alb"]
  }
}

data "aws_lb_target_groups" "existing_tg" {
  filter {
    name   = "name"
    values = ["smart-inventory-tg"]
  }
}

# --- LOCALS ---

locals {
  inventory_sg_id = length(data.aws_security_groups.existing_inventory_sg.ids) > 0 ? data.aws_security_groups.existing_inventory_sg.ids[0] : aws_security_group.inventory_sg[0].id
  alb_sg_id       = length(data.aws_security_groups.existing_alb_sg.ids) > 0 ? data.aws_security_groups.existing_alb_sg.ids[0] : aws_security_group.alb_sg[0].id
  alb_arn         = length(data.aws_lbs.existing_alb.arns) > 0 ? data.aws_lbs.existing_alb.arns[0] : aws_lb.inventory_alb[0].arn
  alb_dns         = length(data.aws_lbs.existing_alb.arns) > 0 ? data.aws_lbs.existing_alb.dns_names[0] : aws_lb.inventory_alb[0].dns_name
  tg_arn          = length(data.aws_lb_target_groups.existing_tg.arns) > 0 ? data.aws_lb_target_groups.existing_tg.arns[0] : aws_lb_target_group.inventory_tg[0].arn
  create_sg       = length(data.aws_security_groups.existing_inventory_sg.ids) == 0
  create_alb_sg   = length(data.aws_security_groups.existing_alb_sg.ids) == 0
  create_alb      = length(data.aws_lbs.existing_alb.arns) == 0
  create_tg       = length(data.aws_lb_target_groups.existing_tg.arns) == 0
}

# --- SECURITY GROUPS ---

resource "aws_security_group" "inventory_sg" {
  count       = local.create_sg ? 1 : 0
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
  count       = local.create_alb_sg ? 1 : 0
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

resource "aws_instance" "controller" {
  count                       = contains(data.aws_instances.existing_instances.tags.Name, "Smart-Inventory-controller") ? 0 : 1
  ami                         = "ami-0c7217cdde317cfec"
  instance_type               = "t3.small"
  vpc_security_group_ids      = [local.inventory_sg_id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.deployer.key_name
  availability_zone           = "us-east-1a"

  tags = {
    Name = "Smart-Inventory-controller"
  }
}

resource "aws_instance" "worker" {
  count                       = contains(data.aws_instances.existing_instances.tags.Name, "Smart-Inventory-worker") ? 0 : 1
  ami                         = "ami-0c7217cdde317cfec"
  instance_type               = "t3.small"
  vpc_security_group_ids      = [local.inventory_sg_id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.deployer.key_name
  availability_zone           = "us-east-1b"

  tags = {
    Name = "Smart-Inventory-worker"
  }
}

resource "aws_ebs_volume" "controller_storage" {
  count             = contains(data.aws_instances.existing_instances.tags.Name, "Smart-Inventory-controller") ? 0 : 1
  availability_zone = aws_instance.controller[0].availability_zone
  size              = 5
  type              = "gp2"
  tags = {
    Name = "smart-inventory-controller-storage"
  }
}

resource "aws_volume_attachment" "controller_storage_attach" {
  count       = contains(data.aws_instances.existing_instances.tags.Name, "Smart-Inventory-controller") ? 0 : 1
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.controller_storage[0].id
  instance_id = aws_instance.controller[0].id
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
  count             = local.create_alb ? 1 : 0
  name               = "smart-inventory-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [local.alb_sg_id]
  subnets            = data.aws_subnets.available.ids

  enable_deletion_protection = false
}

resource "aws_lb_target_group" "inventory_tg" {
  count       = local.create_tg ? 1 : 0
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
  value = local.alb_dns
}

resource "aws_lb_target_group_attachment" "inventory_controller" {
  count            = local.create_tg ? 1 : 0
  target_group_arn = local.tg_arn
  target_id        = contains(data.aws_instances.existing_instances.tags.Name, "Smart-Inventory-controller") ? data.aws_instances.existing_instances.ids[index(data.aws_instances.existing_instances.tags.Name, "Smart-Inventory-controller")] : aws_instance.controller[0].id
  port             = 30080
}

resource "aws_lb_target_group_attachment" "inventory_worker" {
  count            = local.create_tg ? 1 : 0
  target_group_arn = local.tg_arn
  target_id        = contains(data.aws_instances.existing_instances.tags.Name, "Smart-Inventory-worker") ? data.aws_instances.existing_instances.ids[index(data.aws_instances.existing_instances.tags.Name, "Smart-Inventory-worker")] : aws_instance.worker[0].id
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
  value = aws_instance.instances["controller"].public_ip
}

output "worker_ip" {
  value = aws_instance.instances["worker"].public_ip
}

output "alb_dns_name" {
  value = aws_lb.inventory_alb.dns_name
}

resource "local_file" "ansible_inventory" {
  filename        = "${path.module}/hosts.ini"
  file_permission = "0644"
  content = <<-EOT
    [controller]
    controller-node ansible_host=${aws_instance.instances["controller"].public_ip} ansible_user=ubuntu ansible_ssh_private_key_file=${path.module}/smart-inventory-key.pem

    [worker]
    worker-node ansible_host=${aws_instance.instances["worker"].public_ip} ansible_user=ubuntu ansible_ssh_private_key_file=${path.module}/smart-inventory-key.pem
    EOT
}
