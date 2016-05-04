# aws-asg-deployer

### What it does:
Deploys to AutoScaling group (ASG) and Elastic Load Balancer (ELB) without downtime.

### How:
* Double the desire instance number in the target ASG
* Waits for the new instances to be healthy in the ASG's associated elb
* Removes the old instances from the ELB and wait for active connections to finish
* Set the ASG desire instance number to the original size

### Requirements:
* Instances must get the new version of your app on startup
* ASG Termination Policies: `OldestLaunchConfiguration, OldestInstance`
* Install Python dependencies `pip install -r /path/to/requirements.txt`
* Set up AWS credentials for boto ->  [Docs](http://boto.cloudhackers.com/en/latest/boto_config_tut.html#credentials)

### Parameters:
Name | Alias | Description
------------ | ------------- | -------------
**-reg** | --region | AWS Region<br>
**-asg** | --autoscaling-group | Name of the ASG


### Example:
`./deploy.py --region eu-west-1 --autoscaling-group your-asg-name`
