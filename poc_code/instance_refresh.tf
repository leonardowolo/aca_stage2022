resource "aws_autoscaling_group" "example" {
  termination_policies      = ["OldestLaunchTemplate"] #["OldestInstance"] 

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 100
    }
    triggers = ["tag"]
  }
}
