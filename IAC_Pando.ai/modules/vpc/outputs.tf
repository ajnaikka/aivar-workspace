output "private_subnets" {
  value = aws_subnet.private_subnets[*].id
}

output "neptune_sg_id" {
  value = aws_security_group.neptune_sg.id
}

output "dms_sg_id" {
  value = aws_security_group.dms_sg.id
}