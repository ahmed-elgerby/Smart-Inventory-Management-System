#!/usr/bin/env bash
set -euo pipefail

CONTROLLER_NAME="Smart-Inventory-controller"
WORKER_NAME="Smart-Inventory-worker"
KEY_FILE="${PWD}/smart-inventory-key.pem"
DEPLOYMENT_ENV="${PWD}/deployment.env"

write_inventory() {
  local controller_ip="$1"
  local worker_ip="$2"

  cat > hosts.ini <<EOF
[controller]
controller-node ansible_host=${controller_ip} ansible_user=ubuntu ansible_ssh_private_key_file=${KEY_FILE}

[worker]
worker-node ansible_host=${worker_ip} ansible_user=ubuntu ansible_ssh_private_key_file=${KEY_FILE}
EOF
}

find_instance_ip() {
  local name="$1"

  aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=${name}" "Name=instance-state-name,Values=running" \
    --query 'Reservations[].Instances[?PublicIpAddress!=`null`].[PublicIpAddress]' \
    --output text | awk 'NF { print $1; exit }'
}

find_alb_dns() {
  aws elbv2 describe-load-balancers \
    --names smart-inventory-alb \
    --query 'LoadBalancers[0].DNSName' \
    --output text 2>/dev/null || true
}

controller_ip="$(find_instance_ip "$CONTROLLER_NAME")"
worker_ip="$(find_instance_ip "$WORKER_NAME")"
alb_dns="$(find_alb_dns)"

if [ -n "$controller_ip" ] && [ -n "$worker_ip" ] && [ -f "$KEY_FILE" ]; then
  echo "Found matching running EC2 instances. Skipping Terraform apply."
  write_inventory "$controller_ip" "$worker_ip"
  {
    echo "SKIPPED_TERRAFORM=true"
    echo "CONTROLLER_IP=${controller_ip}"
    echo "WORKER_IP=${worker_ip}"
    echo "ALB_DNS=${alb_dns}"
  } > "$DEPLOYMENT_ENV"
  exit 0
fi

if [ -n "$controller_ip" ] && [ -n "$worker_ip" ] && [ ! -f "$KEY_FILE" ]; then
  echo "Matching EC2 instances exist, but ${KEY_FILE} is missing. Terraform will run so Ansible gets a usable key/inventory."
else
  echo "No complete reusable EC2 pair found. Running Terraform."
fi

terraform init -input=false
terraform plan -input=false -out=tfplan
terraform apply -input=false -auto-approve tfplan

{
  echo "SKIPPED_TERRAFORM=false"
  echo "CONTROLLER_IP=$(terraform output -raw controller_ip)"
  echo "WORKER_IP=$(terraform output -raw worker_ip)"
  echo "ALB_DNS=$(terraform output -raw aws_lb_inventory_alb_dns_name)"
} > "$DEPLOYMENT_ENV"
