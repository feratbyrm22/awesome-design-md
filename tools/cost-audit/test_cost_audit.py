"""Offline tests using moto (a fake AWS). Run: pytest tools/cost-audit"""
import os

import boto3
import pytest
from moto import mock_aws

import cost_audit as ca

REGION = "us-east-1"


@pytest.fixture(autouse=True)
def fake_creds(monkeypatch):
    for k, v in {"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
                 "AWS_DEFAULT_REGION": REGION}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("AWS_PROFILE", raising=False)


@mock_aws
def test_finds_waste_and_ignores_used_resources():
    ec2 = boto3.client("ec2", region_name=REGION)
    # waste: unattached 100 GiB gp3 volume, unassociated EIP
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=100, VolumeType="gp3")
    ec2.allocate_address(Domain="vpc")
    # waste: stopped instance
    ami = ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]
    iid = ec2.run_instances(ImageId=ami, MinCount=1, MaxCount=1,
                            InstanceType="t3.micro")["Instances"][0]["InstanceId"]
    ec2.stop_instances(InstanceIds=[iid])
    # not waste: EIP attached to a running instance
    iid2 = ec2.run_instances(ImageId=ami, MinCount=1, MaxCount=1,
                             InstanceType="t3.micro")["Instances"][0]["InstanceId"]
    alloc = ec2.allocate_address(Domain="vpc")["AllocationId"]
    ec2.associate_address(AllocationId=alloc, InstanceId=iid2)
    # waste: log group with no retention (min-log-gb 0 so empty group counts)
    boto3.client("logs", region_name=REGION).create_log_group(logGroupName="/app/forever")

    findings = ca.main(["--regions", REGION, "--min-log-gb", "0"])
    issues = {(f.service, f.issue.split(" (")[0]) for f in findings}

    assert ("EBS", "Unattached volume") in issues
    assert ("Elastic IP", "Unassociated Elastic IP") in issues
    assert ("EC2", "Stopped instance") in issues
    assert ("CloudWatch Logs", "No retention policy") in issues
    eips = [f for f in findings if f.service == "Elastic IP"]
    assert len(eips) == 1 and eips[0].resource_id != alloc
    vol = next(f for f in findings if f.issue == "Unattached volume")
    assert vol.monthly_usd == 8.0  # 100 GiB * $0.08


@mock_aws
def test_guard_blocks_writes():
    session = ca.make_session(None)
    ec2 = session.client("ec2", region_name=REGION)
    ec2.describe_volumes()  # read is fine
    with pytest.raises(ca.WriteAttemptBlocked):
        ec2.create_volume(AvailabilityZone="us-east-1a", Size=1)
    with pytest.raises(ca.WriteAttemptBlocked):
        session.client("s3", region_name=REGION).delete_bucket(Bucket="x")
