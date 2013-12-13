#!/usr/bin/env python
# coding: utf-8

__license__ = """
Copyright (c) 2013 Will Maier <wcmaier@m.aier.us>

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

import os
import random

import boto.ec2
import boto.https_connection as https

from boto import config

EC2_ENDPOINT = None
EC2_ENDPOINT_ADDRESS = None
ZONE = None
TTL = None
ec2 = None

def init(id, cfg):
    global EC2_ENDPOINT
    global EC2_ENDPOINT_ADDRESS
    global ZONE
    global TTL
    global ec2

    EC2_ENDPOINT = os.environ.get("EC2_ENDPOINT", "ec2.us-east-1.amazonaws.com").encode("ascii")
    EC2_ENDPOINT_ADDRESS = os.environ.get("EC2_ENDPOINT_ADDRESS", "").encode("ascii")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1").encode("ascii")
    ZONE = os.environ.get("ZONE", ".example.com.").encode("ascii")
    TTL = int(os.environ.get("TTL", "300"))

    ca_certificates_file = config.get_value(
        'Boto',
        'ca_certificates_file',
        boto.connection.DEFAULT_CA_CERTS_FILE
    )

    ec2 = connect_to_ec2(
        endpoint=EC2_ENDPOINT,
        address=EC2_ENDPOINT_ADDRESS,
        ca_certificates_file=ca_certificates_file,
    )

    if not ZONE.endswith("."):
        ZONE += "."

    log_info("unbound_ec2: connected to EC2 endpoint %s" % EC2_ENDPOINT)
    log_info("unbound_ec2: authoritative for zone %s" % ZONE)

    return True

def deinit(id): return True

def inform_super(id, qstate, superqstate, qdata): return True

def operate(id, event, qstate, qdata):
    global ZONE

    if (event == MODULE_EVENT_NEW) or (event == MODULE_EVENT_PASS):
        if (qstate.qinfo.qtype == RR_TYPE_A) or (qstate.qinfo.qtype == RR_TYPE_ANY):
            qname = qstate.qinfo.qname_str
            if qname.endswith(ZONE):
                log_info("unbound_ec2: handling forward query for %s" % qname)
                return handle_forward(id, event, qstate, qdata)

        # Fall through; pass on this request.
        return handle_pass(id, event, qstate, qdata)

    if event == MODULE_EVENT_MODDONE:
        return handle_finished(id, event, qstate, qdata)

    return handle_error(id, event, qstate, qdata)


def determine_address(instance):
    return (instance.tags.get('Address')
            or instance.ip_address
            or instance.private_ip_address).encode("ascii")


def handle_forward(id, event, qstate, qdata):
    global TTL

    qname = qstate.qinfo.qname_str
    msg = DNSMessage(qname, RR_TYPE_A, RR_CLASS_IN, PKT_QR | PKT_RA | PKT_AA)

    reservations = ec2.get_all_instances(filters={
        "instance-state-name": "running",
        "tag:Name": qname.strip("."),
    })
    instances = [instance for reservation in reservations
                 for instance in reservation.instances]

    if len(instances) == 0:
        qstate.return_rcode = RCODE_NXDOMAIN
    else:
        qstate.return_rcode = RCODE_NOERROR
        random.shuffle(instances)
        for instance in instances:
            address = determine_address(instance)
            record = "%s %d IN A %s" % (qname, TTL, address)
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


class Connection(https.CertValidatingHTTPSConnection):
    """An EC2 connection.

    This implementation supports odd cases where `host` is the correct
    name (or address) for the server but another name should be used to
    validate the server's certificate. Then, `hostname` is used
    instead. This is necessary when `host` is an IP address.
    """

    def __init__(self,
                 host,
                 hostname=None,
                 **kwargs):
        self.hostname = hostname
        https.CertValidatingHTTPSConnection.__init__(self, host, **kwargs)

    def connect(self):
        try:
            https.CertValidatingHTTPSConnection.connect(self)
        except https.InvalidCertificateException, e:
            if not https.ValidateCertificateHostname(e.cert, self.hostname):
                raise

def conn_factory(hostname=None, ca_certificates_file=None):
    def factory(host, **kwargs):
        return Connection(
            host,
            hostname=hostname,
            ca_certs=ca_certificates_file,
            **kwargs)
    return factory, ()

def connect_to_ec2(endpoint, address=None, ca_certificates_file=None):
    if not address:
        address = endpoint
    region = boto.ec2.RegionInfo(
        endpoint=address,
        )
    return boto.ec2.EC2Connection(
        region=region,
        https_connection_factory=conn_factory(
            hostname=endpoint,
            ca_certificates_file=ca_certificates_file,
            ),
    )
