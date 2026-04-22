resource "aws_instance" "app_server" {
  ami           = "ami-0c7217cdde317cfec"
  instance_type = "t2.micro"
  vpc_security_group_ids = [aws_security_group.inventory_sg.id]

  tags = {
    Name = "Smart-Inventory-Server"
  }
}

resource "aws_security_group" "inventory_sg" {
  name        = "inventory-sg"
  description = "Allow Web Traffic"

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
