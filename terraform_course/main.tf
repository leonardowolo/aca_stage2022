provider "aws" {
  region = "us-east-1"
}
resource "aws_instance" "vm" {
  ami           = "ami-0e322da50e0e90e21"
  subnet_id     = "subnet-01f1385cee60cd1d7"
  instance_type = "t3.micro"
  tags = {
    Name = "my-first-tf-node"
  }
}
