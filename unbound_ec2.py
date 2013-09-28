#!/usr/bin/env python
# coding: utf-8

import boto.ec2

region = "us-east-1"
authoritative = "dev.example.com."
ec2 = None

def init(id, cfg):
    global ec2
    ec2 = boto.ec2.connect_to_region(region)

    return True

def deinit(id): return True

def inform_super(id, qstate, superqstate, qdata): return True

# forward: ec2.get_all_instances(filters={"tag:example:env": "prod", "instance-state-name": "running", "tag:Name": name})
# reverse: ec2.get_all_instances(filters={"tag:example:env": "prod", "instance-state-name": "running", "private-ip-address": ipaddr})
# what about public addrs?
# http://unbound.net/documentation/pythonmod/modules/struct.html
# http://jpmens.net/2011/08/09/extending-unbound-with-python-module/
def operate(id, event, qstate, qdata):
    if (event == MODULE_EVENT_NEW) or (event == MODULE_EVENT_PASS):
        if (qstate.qinfo.qtype == RR_TYPE_A) or (qstate.qinfo.qtype == RR_TYPE_ANY):
            qname = qstate.qinfo.qname_str
            if qname.endswith(authoritative):
                return handle_forward(id, event, qstate, qdata)

        elif (qstate.qinfo.qtype == RR_TYPE_PTR):
            # XXX what if we don't know?
            return handle_reverse(id, event, qstate, qdata)

        # Fall through; pass on this request.    
        return handle_pass(id, event, qstate, qdata)

    if event == MODULE_EVENT_MODDONE:
        return handle_finished(id, event, qstate, qdata)

    return handle_error(id, event, qstate, qdata)

def handle_forward(id, event, qstate, qdata):
    name = qstate.qinfo.qname_str
    base = name[:-len(authoritative)]
    
    msg = DNSMessage(qstate.qinfo.qname_str, RR_TYPE_A, RR_CLASS_IN, PKT_QR | PKT_RA | PKT_AA)

    reservations = ec2.get_all_instances(filters={
        "instance-state-name": "running",
        "tag:Name": name,
    })
    instances = [instance for reservation in reservations
                 for instance in reservation.instances]

    if len(instances) == 0:
        qstate.return_rcode = RCODE_NXDOMAIN
    else:
        qstate.return_rcode = RCODE_NOERROR
        for instance in instances:
            msg.answer.append("%s %d IN A %s" % (
                ttl,
                qstate.qinfo.qname_str,
                instance.private_ip_address))

    #set qstate.return_msg 
    if not msg.set_return_msg(qstate):
        qstate.ext_state[id] = MODULE_ERROR 
        return True

    #we don't need validation, result is valid
    qstate.return_msg.rep.security = 2

    qstate.return_rcode = RCODE_NOERROR
    qstate.ext_state[id] = MODULE_FINISHED 
    return True

def handle_reverse(id, event, qstate, qdata):
    msg.answer.append("140.135.55.23.in-addr.arpa. 300	IN	PTR	a23-55-135-140.deploy.static.akamaitechnologies.com.")
    return True

def handle_pass(id, event, qstate, qdata):
    qstate.ext_state[id] = MODULE_WAIT_MODULE 
    return True

def handle_finished(id, event, qstate, qdata):
    log_info("unbound_ec2: iterator module done")
    qstate.ext_state[id] = MODULE_FINISHED 
    return True

def handle_error(id, event, qstate, qdata):      
    log_err("unbound_ec2: bad event")
    qstate.ext_state[id] = MODULE_ERROR
    return True
