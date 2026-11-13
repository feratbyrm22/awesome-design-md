#!/usr/bin/env python3
"""
Read-only AWS cost audit: finds idle / orphaned resources that keep billing.

SAFETY: every AWS API call goes through a guard that only allows
Describe*/List*/Get* operations. Anything else (Delete, Stop, Modify, ...)
raises before the request is sent. This script never changes your account.

Usage:
    python cost_audit.py                       # all enabled regions
    python cost_audit.py --regions us-east-1 eu-central-1
    python cost_audit.py --profile prod --json report.json --csv report.csv

Required IAM: the AWS managed policy "ReadOnlyAccess" (or "ViewOnlyAccess"
plus cloudwatch:GetMetricStatistics) is enough.

Cost figures are ESTIMATES based on us-east-1 on-demand list prices
(see PRICES below). Check the real numbers in Cost Explorer before acting.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

# ---------------------------------------------------------------------------
# Read-only guard
# ---------------------------------------------------------------------------
READ_ONLY_PREFIXES = ("Describe", "List", "Get", "Lookup")


class WriteAttemptBlocked(RuntimeError):
    pass


def _guard(model, **_):
    if not model.name.startswith(READ_ONLY_PREFIXES):
        raise WriteAttemptBlocked(
            f"Blocked non read-only AWS call: {model.service_model.service_name}.{model.name}"
        )


def make_session(profile: str | None) -> boto3.Session:
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    # Registered on the session's event system, so it applies to every client.
    session.events.register("before-parameter-build.*.*", _guard)
    return session


# ---------------------------------------------------------------------------
# Price table (USD, us-east-1 on-demand, approximate)
# ---------------------------------------------------------------------------
PRICES = {
    "ebs_gb_month": {"gp2": 0.10, "gp3": 0.08, "io1": 0.125, "io2": 0.125,
                     "st1": 0.045, "sc1": 0.015, "standard": 0.05},
    "snapshot_gb_month": 0.05,
    "eip_hour": 0.005,            # every public IPv4 is billed since Feb 2024
    "nat_hour": 0.045,
    "alb_hour": 0.0225,
    "nlb_hour": 0.0225,
    "clb_hour": 0.025,
    "rds_storage_gb_month": 0.115,
    "rds_snapshot_gb_month": 0.095,
    "logs_gb_month": 0.03,
}
HOURS_PER_MONTH = 730

# Rough on-demand $/hour for common instance sizes; unknown types get None.
EC2_HOURLY = {
    "t3.nano": 0.0052, "t3.micro": 0.0104, "t3.small": 0.0208, "t3.medium": 0.0416,
    "t3.large": 0.0832, "t3.xlarge": 0.1664, "t3.2xlarge": 0.3328,
    "t2.micro": 0.0116, "t2.small": 0.023, "t2.medium": 0.0464, "t2.large": 0.0928,
    "m5.large": 0.096, "m5.xlarge": 0.192, "m5.2xlarge": 0.384, "m5.4xlarge": 0.768,
    "m6i.large": 0.096, "m6i.xlarge": 0.192, "m6i.2xlarge": 0.384,
    "c5.large": 0.085, "c5.xlarge": 0.17, "c5.2xlarge": 0.34,
    "r5.large": 0.126, "r5.xlarge": 0.252, "r5.2xlarge": 0.504,
    "g4dn.xlarge": 0.526, "g5.xlarge": 1.006, "p3.2xlarge": 3.06,
}
RDS_HOURLY = {
    "db.t3.micro": 0.017, "db.t3.small": 0.034, "db.t3.medium": 0.068,
    "db.t3.large": 0.136, "db.m5.large": 0.171, "db.m5.xlarge": 0.342,
    "db.r5.large": 0.24, "db.r5.xlarge": 0.48,
}


@dataclass
class Finding:
    region: str
    service: str
    resource_id: str
    issue: str
    monthly_usd: float | None
    detail: str = ""
    tags: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now() -> datetime:
    return datetime.now(timezone.utc)


def tags_of(obj) -> dict:
    return {t["Key"]: t["Value"] for t in (obj.get("Tags") or obj.get("TagList") or [])}


def paginate(client, op, key, **kw):
    for page in client.get_paginator(op).paginate(**kw):
        yield from page.get(key, [])


def metric_sum(cw, namespace, metric, dims, days, stat="Sum"):
    """Sum (or max) of a metric over the last `days`. None if no datapoints."""
    resp = cw.get_metric_statistics(
        Namespace=namespace, MetricName=metric, Dimensions=dims,
        StartTime=now() - timedelta(days=days), EndTime=now(),
        Period=86400, Statistics=[stat],
    )
    pts = [p[stat] for p in resp.get("Datapoints", [])]
    if not pts:
        return None
    return max(pts) if stat == "Maximum" else sum(pts)


def metric_avg(cw, namespace, metric, dims, days):
    resp = cw.get_metric_statistics(
        Namespace=namespace, MetricName=metric, Dimensions=dims,
        StartTime=now() - timedelta(days=days), EndTime=now(),
        Period=86400, Statistics=["Average"],
    )
    pts = [p["Average"] for p in resp.get("Datapoints", [])]
    return sum(pts) / len(pts) if pts else None


def money(v):
    return None if v is None else round(v, 2)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def check_ebs(ec2, region, args):
    out = []
    for v in paginate(ec2, "describe_volumes", "Volumes"):
        price = PRICES["ebs_gb_month"].get(v["VolumeType"], 0.10)
        cost = v["Size"] * price
        if v["State"] == "available":
            out.append(Finding(region, "EBS", v["VolumeId"], "Unattached volume",
                               money(cost), f'{v["Size"]} GiB {v["VolumeType"]}, created {v["CreateTime"]:%Y-%m-%d}',
                               tags_of(v)))
        elif v["VolumeType"] == "gp2":
            out.append(Finding(region, "EBS", v["VolumeId"], "gp2 volume (gp3 is ~20% cheaper)",
                               money(v["Size"] * (0.10 - 0.08)), f'{v["Size"]} GiB, potential saving',
                               tags_of(v)))
    return out


def check_snapshots(ec2, region, args):
    out = []
    cutoff = now() - timedelta(days=args.snapshot_days)
    ami_snaps = set()
    for img in paginate(ec2, "describe_images", "Images", Owners=["self"]):
        for bdm in img.get("BlockDeviceMappings", []):
            sid = bdm.get("Ebs", {}).get("SnapshotId")
            if sid:
                ami_snaps.add(sid)
    live_vols = {v["VolumeId"] for v in paginate(ec2, "describe_volumes", "Volumes")}
    for s in paginate(ec2, "describe_snapshots", "Snapshots", OwnerIds=["self"]):
        if s["StartTime"] > cutoff or s["SnapshotId"] in ami_snaps:
            continue
        orphan = s.get("VolumeId") not in live_vols
        out.append(Finding(region, "EBS Snapshot", s["SnapshotId"],
                           f'Older than {args.snapshot_days} days' + (", source volume deleted" if orphan else ""),
                           # Snapshots are incremental: VolumeSize is an upper bound.
                           money(s["VolumeSize"] * PRICES["snapshot_gb_month"]),
                           f'{s["VolumeSize"]} GiB (upper bound), {s["StartTime"]:%Y-%m-%d}',
                           tags_of(s)))
    return out


def check_eips(ec2, region, args):
    out = []
    for a in ec2.describe_addresses().get("Addresses", []):
        if not a.get("AssociationId"):
            out.append(Finding(region, "Elastic IP", a.get("AllocationId", a.get("PublicIp")),
                               "Unassociated Elastic IP",
                               money(PRICES["eip_hour"] * HOURS_PER_MONTH), a.get("PublicIp", ""),
                               tags_of(a)))
    return out


def check_ec2(ec2, cw, region, args):
    out = []
    vols = {v["VolumeId"]: v for v in paginate(ec2, "describe_volumes", "Volumes")}
    for res in paginate(ec2, "describe_instances", "Reservations"):
        for i in res["Instances"]:
            iid, itype, state = i["InstanceId"], i["InstanceType"], i["State"]["Name"]
            if state == "stopped":
                gb = sum(vols.get(b["Ebs"]["VolumeId"], {}).get("Size", 0)
                         for b in i.get("BlockDeviceMappings", []) if "Ebs" in b)
                out.append(Finding(region, "EC2", iid, "Stopped instance (EBS still billed)",
                                   money(gb * 0.10), f"{itype}, {gb} GiB attached, "
                                   f"reason: {i.get('StateTransitionReason', '')}", tags_of(i)))
            elif state == "running":
                dims = [{"Name": "InstanceId", "Value": iid}]
                avg = metric_avg(cw, "AWS/EC2", "CPUUtilization", dims, args.days)
                peak = metric_sum(cw, "AWS/EC2", "CPUUtilization", dims, args.days, "Maximum")
                if avg is not None and avg < args.cpu_threshold and (peak or 0) < 20:
                    hourly = EC2_HOURLY.get(itype)
                    out.append(Finding(region, "EC2", iid,
                                       f"Idle: avg CPU {avg:.1f}% / peak {peak or 0:.1f}% over {args.days}d",
                                       money(hourly * HOURS_PER_MONTH) if hourly else None,
                                       itype + ("" if hourly else " (price not in table)"), tags_of(i)))
    return out


def check_nat(ec2, cw, region, args):
    out = []
    for n in paginate(ec2, "describe_nat_gateways", "NatGateways",
                      Filter=[{"Name": "state", "Values": ["available"]}]):
        dims = [{"Name": "NatGatewayId", "Value": n["NatGatewayId"]}]
        b = metric_sum(cw, "AWS/NATGateway", "BytesOutToDestination", dims, args.days) or 0
        if b < 1024 ** 3:  # < 1 GiB in the window
            out.append(Finding(region, "NAT Gateway", n["NatGatewayId"],
                               f"Near-zero traffic ({b / 1024 ** 2:.1f} MiB in {args.days}d)",
                               money(PRICES["nat_hour"] * HOURS_PER_MONTH), n.get("VpcId", ""), tags_of(n)))
    return out


def check_elbv2(elb, cw, region, args):
    out = []
    for lb in paginate(elb, "describe_load_balancers", "LoadBalancers"):
        arn, kind = lb["LoadBalancerArn"], lb["Type"]
        if kind not in ("application", "network"):
            continue
        healthy = 0
        tgs = elb.describe_target_groups(LoadBalancerArn=arn).get("TargetGroups", [])
        for tg in tgs:
            th = elb.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
            healthy += sum(1 for t in th["TargetHealthDescriptions"]
                           if t["TargetHealth"]["State"] == "healthy")
        dim_val = arn.split(":loadbalancer/")[-1]
        ns, metric = (("AWS/ApplicationELB", "RequestCount") if kind == "application"
                      else ("AWS/NetworkELB", "NewFlowCount"))
        traffic = metric_sum(cw, ns, metric, [{"Name": "LoadBalancer", "Value": dim_val}], args.days) or 0
        if healthy == 0 or traffic == 0:
            why = "no healthy targets" if healthy == 0 else f"0 requests in {args.days}d"
            hourly = PRICES["alb_hour"] if kind == "application" else PRICES["nlb_hour"]
            out.append(Finding(region, f"{kind.upper()[:1]}LB", lb["LoadBalancerName"],
                               f"Unused load balancer ({why})", money(hourly * HOURS_PER_MONTH),
                               f"{len(tgs)} target groups", {}))
    return out


def check_clb(elb, region, args):
    out = []
    for lb in paginate(elb, "describe_load_balancers", "LoadBalancerDescriptions"):
        if not lb.get("Instances"):
            out.append(Finding(region, "CLB", lb["LoadBalancerName"], "Classic LB with no instances",
                               money(PRICES["clb_hour"] * HOURS_PER_MONTH), "", {}))
    return out


def check_rds(rds, cw, region, args):
    out = []
    for db in paginate(rds, "describe_db_instances", "DBInstances"):
        dbid, cls = db["DBInstanceIdentifier"], db["DBInstanceClass"]
        storage = db.get("AllocatedStorage", 0) * PRICES["rds_storage_gb_month"]
        hourly = RDS_HOURLY.get(cls)
        multi = 2 if db.get("MultiAZ") else 1
        compute = hourly * HOURS_PER_MONTH * multi if hourly else None
        if db["DBInstanceStatus"] == "stopped":
            out.append(Finding(region, "RDS", dbid,
                               "Stopped DB (storage still billed; AWS auto-starts it after 7 days)",
                               money(storage), cls, tags_of(db)))
            continue
        conns = metric_sum(cw, "AWS/RDS", "DatabaseConnections",
                           [{"Name": "DBInstanceIdentifier", "Value": dbid}], args.days, "Maximum")
        if conns is not None and conns == 0:
            total = (compute or 0) + storage
            out.append(Finding(region, "RDS", dbid, f"0 connections in {args.days}d",
                               money(total) if compute else None,
                               f"{cls}{' Multi-AZ' if multi == 2 else ''}, {db.get('AllocatedStorage')} GiB",
                               tags_of(db)))
    cutoff = now() - timedelta(days=args.snapshot_days)
    for s in paginate(rds, "describe_db_snapshots", "DBSnapshots", SnapshotType="manual"):
        t = s.get("SnapshotCreateTime")
        if t and t < cutoff:
            out.append(Finding(region, "RDS Snapshot", s["DBSnapshotIdentifier"],
                               f"Manual snapshot older than {args.snapshot_days} days",
                               money(s.get("AllocatedStorage", 0) * PRICES["rds_snapshot_gb_month"]),
                               f'{s.get("AllocatedStorage")} GiB, {t:%Y-%m-%d}', tags_of(s)))
    return out


def check_logs(logs, region, args):
    out = []
    for g in paginate(logs, "describe_log_groups", "logGroups"):
        gb = g.get("storedBytes", 0) / 1024 ** 3
        if "retentionInDays" not in g and gb >= args.min_log_gb:
            out.append(Finding(region, "CloudWatch Logs", g["logGroupName"],
                               "No retention policy (kept forever)",
                               money(gb * PRICES["logs_gb_month"]), f"{gb:.2f} GB stored", {}))
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def audit_region(session, region, args, errors):
    cfg = Config(region_name=region, retries={"max_attempts": 8, "mode": "adaptive"})
    ec2 = session.client("ec2", config=cfg)
    cw = session.client("cloudwatch", config=cfg)
    checks = [
        ("ebs", lambda: check_ebs(ec2, region, args)),
        ("snapshots", lambda: check_snapshots(ec2, region, args)),
        ("eip", lambda: check_eips(ec2, region, args)),
        ("ec2", lambda: check_ec2(ec2, cw, region, args)),
        ("nat", lambda: check_nat(ec2, cw, region, args)),
        ("elbv2", lambda: check_elbv2(session.client("elbv2", config=cfg), cw, region, args)),
        ("clb", lambda: check_clb(session.client("elb", config=cfg), region, args)),
        ("rds", lambda: check_rds(session.client("rds", config=cfg), cw, region, args)),
        ("logs", lambda: check_logs(session.client("logs", config=cfg), region, args)),
    ]
    findings = []
    for name, fn in checks:
        try:
            findings.extend(fn())
        except WriteAttemptBlocked:
            raise
        except (ClientError, BotoCoreError) as e:
            errors.append(f"{region}/{name}: {e}")
    return findings


def list_regions(session):
    ec2 = session.client("ec2", region_name="us-east-1")
    return sorted(r["RegionName"] for r in ec2.describe_regions(AllRegions=False)["Regions"])


def print_table(findings):
    if not findings:
        print("No idle resources found.")
        return
    findings = sorted(findings, key=lambda f: -(f.monthly_usd or 0))
    rows = [("REGION", "SERVICE", "RESOURCE", "ISSUE", "$/MONTH", "DETAIL")]
    for f in findings:
        rows.append((f.region, f.service, f.resource_id, f.issue,
                     "?" if f.monthly_usd is None else f"{f.monthly_usd:,.2f}", f.detail))
    widths = [min(max(len(str(r[i])) for r in rows), 60) for i in range(len(rows[0]))]
    for r in rows:
        print("  ".join(str(c)[:60].ljust(w) for c, w in zip(r, widths)))


def summary(findings):
    by_service: dict[str, float] = {}
    for f in findings:
        by_service[f.service] = by_service.get(f.service, 0) + (f.monthly_usd or 0)
    total = sum(by_service.values())
    unknown = sum(1 for f in findings if f.monthly_usd is None)
    print("\nEstimated monthly waste by service:")
    for svc, v in sorted(by_service.items(), key=lambda kv: -kv[1]):
        print(f"  {svc:<18} ${v:>10,.2f}")
    print(f"  {'TOTAL':<18} ${total:>10,.2f}  (~${total * 12:,.0f}/year)")
    if unknown:
        print(f"  + {unknown} finding(s) without a price estimate")
    return total


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Read-only AWS idle-resource cost audit")
    p.add_argument("--profile")
    p.add_argument("--regions", nargs="*", help="default: all enabled regions")
    p.add_argument("--days", type=int, default=14, help="metric look-back window (default 14)")
    p.add_argument("--cpu-threshold", type=float, default=5.0, help="avg CPU %% below = idle")
    p.add_argument("--snapshot-days", type=int, default=90)
    p.add_argument("--min-log-gb", type=float, default=1.0)
    p.add_argument("--json")
    p.add_argument("--csv")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    session = make_session(args.profile)
    regions = args.regions or list_regions(session)
    findings, errors = [], []
    for r in regions:
        print(f"Scanning {r} ...", file=sys.stderr)
        findings.extend(audit_region(session, r, args, errors))

    print_table(findings)
    total = summary(findings)

    if errors:
        print(f"\n{len(errors)} check(s) failed (usually missing permissions):", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"generated_at": now().isoformat(), "estimated_monthly_usd": round(total, 2),
                       "findings": [asdict(f) for f in findings], "errors": errors},
                      fh, indent=2, default=str)
    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(asdict(findings[0]).keys()) if findings
                               else [f for f in Finding.__dataclass_fields__])
            w.writeheader()
            for f in findings:
                row = asdict(f)
                row["tags"] = json.dumps(row["tags"])
                w.writerow(row)
    return findings


if __name__ == "__main__":
    main()
