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
    from_port   = 30080
    to_port     = 30080
    protocol    = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
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
  for_each                    = toset(["controller", "worker"])
  ami                         = "ami-0c7217cdde317cfec" # Ensure this is a valid Ubuntu AMI
  instance_type               = "t3.small" 
  vpc_security_group_ids      = [aws_security_group.inventory_sg.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.deployer.key_name
  availability_zone           = each.key == "controller" ? "us-east-1a" : "us-east-1b"

  tags = {
    Name = "Smart-Inventory-${each.value}"
  }
}

resource "aws_ebs_volume" "controller_storage" {
  availability_zone = aws_instance.instances["controller"].availability_zone
  size              = 5
  type              = "gp2"
  tags = {
    Name = "smart-inventory-controller-storage"
  }
}

resource "aws_volume_attachment" "controller_storage_attach" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.controller_storage.id
  instance_id = aws_instance.instances["controller"].id
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
    values = [
      aws_instance.instances["controller"].availability_zone,
      aws_instance.instances["worker"].availability_zone
    ]
  }
}

# --- LOAD BALANCER ---

resource "aws_lb" "inventory_alb" {
  name               = "smart-inventory-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
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
  target_id        = aws_instance.instances["controller"].id
  port             = 30080
}

resource "aws_lb_target_group_attachment" "inventory_worker" {
  target_group_arn = aws_lb_target_group.inventory_tg.arn
  target_id        = aws_instance.instances["worker"].id
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
