#!/usr/bin/python
import sys
import time
import logging
import requests
import argparse
import boto
import boto.ec2
import boto.ec2.elb
import boto.ec2.autoscale
from retrying import retry

parser = argparse.ArgumentParser(description='Double ASG instance number, wait until they are healthy and return to the original size')
parser.add_argument('-asg', '--autoscaling-group',required=True, help='AWS Autoscaling Group Name')
parser.add_argument('-reg', '--region',           required=True, help='AWS Region')

args = parser.parse_args()
AWS_ASG = args.autoscaling_group
AWS_REGION = args.region

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)-5s - %(message)s')

def main():
    start = time.time()

    group = getASG(getASGConn())
    instance_ids = get_asg_instance_ids(group)
    logging.info("Instances before start: {}".format(instance_ids))
    desired_capacity_old = group.desired_capacity
    desired_capacity_new = desired_capacity_old * 2

    logging.info("Setting ASG desired capacity from {} to {}".format(desired_capacity_old, desired_capacity_new))
    set_desired_capacity(desired_capacity_new)

    logging.info("Checking for instance count in ASG to be ok")
    check_instance_count_in_asg()

    logging.info("Checking for instance count in ELB to be ok")
    check_instance_count_in_elb(desired_capacity_new)

    logging.info("Checking ELB instances to be healthy")
    check_instance_state_in_elb()
    effective_end = time.time()

    logging.info("Removing instances from ELB to drain connections")
    remove_old_instances_from_elb(group, instance_ids)

    logging.info("Setting ASG desired capacity back to {}".format(desired_capacity_old))
    set_desired_capacity(desired_capacity_old)

    logging.info("Checking for instance count to be ok")
    check_instance_count_in_asg()
    end = time.time()

    logging.info("deploy done in {}s (effective: {}s)!".format(int(end - start), int(effective_end - start) ))

@retry(stop_max_delay=6000000, wait_fixed=10000) # wait 10min with 10 secs betwen attempts
def check_instance_count_in_asg():
    group = getASG(getASGConn())
    instance_ids = get_asg_instance_ids(group)
    logging.debug("ASG Instance_ids: {}".format(instance_ids))
    if len(instance_ids) != group.desired_capacity:
        logging.info("ASG number of instances != desired capacity")
        raise Exception("ASG number of instances != desired capacity")

@retry(stop_max_delay=6000000, wait_fixed=10000) # wait 10min with 10 secs betwen attempts
def check_instance_count_in_elb(expected_count):
    group = getASG(getASGConn())
    balancers = getELBConn().get_all_load_balancers(load_balancer_names=group.load_balancers)
    for elb in balancers:
        if len(elb.instances) != expected_count:
            logging.info("ELB number of instances != desired capacity")
            raise Exception("ELB number of instances != desired capacity")

@retry(stop_max_delay=6000000, wait_fixed=10000) # wait 10min with 10 secs betwen attempts
def check_instance_state_in_elb():
    group = getASG(getASGConn())
    balancers = getELBConn().get_all_load_balancers(load_balancer_names=group.load_balancers)
    for elb in balancers:
        logging.info("Checking in {}: {}".format(elb, elb.instances))
        for instance in elb.instances:
            health = elb.get_instance_health([instance.id])[0]
            logging.info("Instance {} -> {}".format(instance.id, health))
            if health.state != "InService":
                raise Exception("Instance {} not InService yet -> {}".format(instance, health.state))

def set_desired_capacity(capacity):
    conn_as = getASGConn()
    group = getASG(conn_as)
    capacity_response = conn_as.set_desired_capacity(AWS_ASG, capacity)
    logging.debug("set_desired_capacity to {} for {}. response: {}".format(capacity, group, capacity_response))

def remove_old_instances_from_elb(group, instance_ids):
    logging.info("remove_old_instances_from_elb. Group elbs: {}. instance_ids: {}".format(group.load_balancers, instance_ids))
    balancers = getELBConn().get_all_load_balancers(load_balancer_names=group.load_balancers)
    for elb in balancers:
        logging.info("ELB instances: {}".format(elb.instances))
        elb.deregister_instances(instance_ids)
        time.sleep(10)

def get_asg_instance_ids(group):
    instance_ids = [instance.instance_id for instance in group.instances]
    return instance_ids

def getASG(conn):
    return conn.get_all_groups(names=[AWS_ASG])[0]

def getASGConn():
    return boto.ec2.autoscale.connect_to_region(AWS_REGION)

def getELBConn():
    return boto.ec2.elb.connect_to_region(AWS_REGION)

def getEC2Conn():
    return boto.ec2.connect_to_region(AWS_REGION)

if __name__ == '__main__':
  main()
