resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# Public Subnets
resource "aws_subnet" "public_subnets" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet("10.0.0.0/21", 3, count.index)
  availability_zone       = "${var.aws_region}${element(["a", "b", "c"], count.index)}"
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${element(["a", "b", "c"], count.index)}"
  }
}

resource "aws_route_table_association" "public_assoc" {
  count          = 3
  subnet_id      = aws_subnet.public_subnets[count.index].id
  route_table_id = aws_route_table.public_rt.id
}

# Private Subnets
resource "aws_subnet" "private_subnets" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet("10.0.8.0/21", 3, count.index)
  availability_zone       = "${var.aws_region}${element(["a", "b", "c"], count.index)}"
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.project_name}-private-subnet-${element(["a", "b", "c"], count.index)}"
  }
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat_eip" {
  #domain = "vpc"  # removed as it is deprecated in latest version providers

  tags = {
    Name = "${var.project_name}-nat-eip"
  }
}


# NAT Gateway in the first public subnet
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnets[0].id
  tags = {
    Name = "${var.project_name}-nat"
  }

  depends_on = [aws_internet_gateway.igw]
}

# Private Route Table
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

# Associate private subnets with private route table
resource "aws_route_table_association" "private_assoc" {
  count          = 3
  subnet_id      = aws_subnet.private_subnets[count.index].id
  route_table_id = aws_route_table.private_rt.id
}





# Security Groups
##########################

resource "aws_security_group" "dms_sg" {
  name        = "${var.project_name}-dms-sg"
  description = "Security group for DMS"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-dms-sg"
  }
}

resource "aws_security_group" "neptune_sg" {
  name        = "${var.project_name}-neptune-sg"
  description = "Security group for Neptune cluster"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 8182
    to_port     = 8182
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-neptune-sg"
  }
}





