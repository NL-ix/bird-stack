BIRD-Proxy
===========

HTTP(S) interface for BIRD Route-Server management

Configuration and installation
-------------------------------

**Development**

Use the `setup_dev.sh` script to set up your configuration files and python
virtualenv. After setup, modify the config file
`/home/$(whoami)/bird-proxy-data/etc/bird-proxy/bird-proxy.yaml`.
Change the token to something of your liking, and change `BIRD_CONFIG_FOLDER` to
`/home/$(whoami)/bird-proxy-data/var/bird` (this directory is automatically
created by `setup_dev.sh`.

To communicate with the BIRD socket file you need to add your user to the
`bird` linux group: `sudo usermod -aG bird $(whoami)`.

After that is done bird-proxy can be run using the `run_dev.sh` script. This
will allow you to communicate to the web API over `http://localhost:8005` (this
is the default port used).

For more advanced usage e.g. proxying, you can set up your webserver to proxy to
`http://localhost:8005`.

**Installing as a package**

The repository contains debian scripts to build a debian package for Ubuntu
16.04. To build a package run the following command:
`dpkg-buildpackage -us -uc -tc -b`
Note: dh-virtualenv >= 1.0 (https://github.com/spotify/dh-virtualenv) is used
for package building. Without this the package cannot be built.

The package can be installed with `dpkg -i` and will set up everything required
to run bird-proxy.

After installation the bird-proxy configuration should be copied in order to
alter the API token in the configuration:
`cp /etc/bird-proxy/defaults/bird-proxy.yaml /etc/bird-proxy/bird-proxy.yaml`

Next, alter the API token in `/etc/bird-proxy/bird-proxy.yaml` for security
reasons.

With everything in place the application can be restarted (it's automatically
started after package installation):
`systemctl restart bird-proxy`

Verify that bird-proxy is running. If not, check `journalctl -xe` for errors.

With bird-proxy running you'll want to set up your nginx template to allow
connections to the bird-proxy instance over http(s). We include an example
nginx configuration in the package, which is installed as
`/etc/nginx/sites-available/bird-proxy.conf`. Copy the file and alter it to your
needs. Do not alter the `proxy_pass` directive; this is how nginx connects to
the bird-proxy instance.
Don't forget to create a symlink in `/etc/nginx/sites-enabled` for your
nginx configuration file and reload nginx!

If you'll be using bird-proxy to deploy configurations it's advised to make
`/etc/bird/bird.conf` and `/etc/bird/bird6.conf` symlinks to ensure BIRD always
uses the latest deployed configuration file on startup. bird-proxy always
creates a symlink file to the latest succesfully deployed config file.
For `bird.conf` this is `/var/bird/bird-ipv4-latest.conf`:
`ln -s /var/bird/bird-ipv4-latest.conf /etc/bird/bird.conf`
For `bird6.conf` this is `/var/bird/bird-ipv6-latest.conf`:
`ln -s /var/bird/bird-ipv6-latest.conf /etc/bird/bird.conf`


Features
---------

All the functions must be called using HTTP `POST`

**BIRD configuration deployment**

*Endpoint*
/deployconfig

*Input*

request body has to include the keys:

- `ip_version`: Version of the BIRD process to affect ('ipv4', 'ipv6')

configuration file must be included in `request.files`

*Output*

JSON response in the following format:

```
{
    "outcome": outcome of the operation (True, False),
    "message": BIRD operations output
 }
```

**Get BGP sessions info**

*Endpoint*
/protocol/info/verbose

*Input*

request body has to include the keys:

- `ip_version`: Version of the BIRD process to affect ('ipv4', 'ipv6')

*Output*

JSON response in the folloing format:

```
{
    "outcome": outcome of the operation (True, False),
    "message": peering session information
 }

Peering session information are in a list of objects in the following format:
    
{
    "as_number": integer,
    "bgp_state": string,
    "description": string,
    "prefixes": {
        "imported": int,
        "exported": int,
        "preferred": int
    },
    "session_name": str,
    "ip_address": str
}
```

Notes
-----

