#!/usr/bin/env python
# coding: utf-8

import os
import boto.ec2

region = os.environ.get("AWS_REGION", "us-east-1")
authoritative = os.environ.get("AUTHORITATIVE", ".example.com.")
ttl = int(os.environ.get("TTL", 60))
ec2 = None

def init(id, cfg):
    global ec2
    global region
    global authoritative

    if not authoritative.endswith("."):
        authoritative += "."
    
    ec2 = boto.ec2.connect_to_region(region)

    log_info("unbound_ec2: connected to AWS region %s" % region)
    log_info("unbound_ec2: authoritative for %s" % authoritative)

    return True

def deinit(id): return True

def inform_super(id, qstate, superqstate, qdata): return True

def operate(id, event, qstate, qdata):
    global authoritative
    
    if (event == MODULE_EVENT_NEW) or (event == MODULE_EVENT_PASS):
        if (qstate.qinfo.qtype == RR_TYPE_A) or (qstate.qinfo.qtype == RR_TYPE_ANY):
            qname = qstate.qinfo.qname_str
            if qname.endswith(authoritative):
                log_info("unbound_ec2: handling forward query for %s" % qname)
                return handle_forward(id, event, qstate, qdata)

        # Fall through; pass on this request.    
        return handle_pass(id, event, qstate, qdata)

    if event == MODULE_EVENT_MODDONE:
        return handle_finished(id, event, qstate, qdata)

    return handle_error(id, event, qstate, qdata)

def handle_forward(id, event, qstate, qdata):
    global ttl
    
    name = qstate.qinfo.qname_str
    msg = DNSMessage(qstate.qinfo.qname_str, RR_TYPE_A, RR_CLASS_IN, PKT_QR | PKT_RA | PKT_AA)

    reservations = ec2.get_all_instances(filters={
        "instance-state-name": "running",
        "tag:Name": name.strip("."),
    })
    instances = [instance for reservation in reservations
                 for instance in reservation.instances]

    if len(instances) == 0:
        qstate.return_rcode = RCODE_NXDOMAIN
    else:
        qstate.return_rcode = RCODE_NOERROR
        for instance in instances:
            address = (instance.ip_address or instance.private_ip_address).encode("ascii")
            record = "%s %d IN A %s" % (name, ttl, address)
            msg.answer.append(record)

    if not msg.set_return_msg(qstate):
        qstate.ext_state[id] = MODULE_ERROR 
        return True

    qstate.return_msg.rep.security = 2
    qstate.ext_state[id] = MODULE_FINISHED 
    return True

def handle_pass(id, event, qstate, qdata):
    qstate.ext_state[id] = MODULE_WAIT_MODULE 
    return True

def handle_finished(id, event, qstate, qdata):
    qstate.ext_state[id] = MODULE_FINISHED 
    return True

def handle_error(id, event, qstate, qdata):      
    log_err("unbound_ec2: bad event")
    qstate.ext_state[id] = MODULE_ERROR
    return True
