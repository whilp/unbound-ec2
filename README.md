# unbound-ec2

This module uses the [Unbound](http://unbound.net) DNS resolver to answer simple DNS queries using EC2 API calls. For example, the following query would match an EC2 instance with a `Name` tag of `foo.example.com`:

```
$ dig -p 5003 @127.0.0.1 foo.example.com.
[1380403735] unbound[23676:0] info: unbound_ec2: handling forward query for foo.example.com.
[1380403735] unbound[23676:0] info: unbound_ec2: found 1 instances for query foo.example.com.
[1380403735] unbound[23676:0] info: unbound_ec2: 10.0.0.1

; <<>> DiG 9.8.1-P1 <<>> -p 5003 @127.0.0.1 foo.example.com.
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 22551
;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;foo.example.com.   IN  A

;; ANSWER SECTION:
foo.example.com. 60 IN  A   10.0.0.1

;; Query time: 235 msec
;; SERVER: 127.0.0.1#5003(127.0.0.1)
;; WHEN: Sat Sep 28 21:28:55 2013
;; MSG SIZE  rcvd: 61
```

## Installation

On Ubuntu, install the `unbound`, `python-unbound`, and `python-boto` system packages. Then, install `unbound_ec2`:

```
wget -qO- https://raw.github.com/whilp/unbound-ec2/master/unbound_ec2.py | sudo tee /path/to/unbound_ec2.py > /dev/null
```

The following settings must be added to your Unbound configuration:

```
server:
    chroot: ""
    module-config: "validator python iterator"

python:
    python-script: "/path/to/unbound_ec2.py"
```

## Testing

This repository includes a test configuration. Run it as follows:

```
unbound -c unbound_ec2.conf
```

## License

```
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
```