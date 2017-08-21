# cloudflare-ddns
This is a continued version of [thatjpk's cloudflare-ddns](https://github.com/thatjpk/cloudflare-ddns).

## Introduction
A script for dynamically updating Cloudflare DNS records.
If you have a dynamic IP and you're hosting servers behind it, it's an easy way to make it 'pseudo-static'.

## Dependencies
You'll need a [Python](https://www.python.org/downloads/) interpreter and the following libraries:
 - [PyYAML](https://bitbucket.org/xi/pyyaml) (`pip install pyyaml`)
 - [Requests](http://docs.python-requests.org/en/latest/) (`pip install
   requests`)
   
You can install them with `pip` :
	pip install -r requirements.txt
	
## Features
  - Two ways to grab your IP address
  	- HTTP 
	- DNS lookup (dig)
  - IPv4 and IPv6 support (A and AAAA records)
  - Logging
  - One configuration file for multiple records
  - Multiple record settings:
  	- Time to Live (TTL)
	- Proxy mode
	- Logging level
  - Lightweight
  - Smart update (your record will only be updated only if needed)

## Usage
First, a few assumptions:
  - You're using Cloudflare to host DNS for a domain you own.
  - You have one or more A/AAAA records in Cloudflare you intend to dynamically update.

To use this utility, create a copy of the `example.com.yml` file inside the `zones` folder and
rename it to your zone name.
To do a one-off update of your DNS record, simply run `python
cloudflare_ddns.py -z example.com` from your terminal.
The script will determine your public IP address and automatically update the records along with it and the settings you provided.

If the program encounters an issue while attempting to update Cloudflare's 
records, you can check the the `logs` folder for more informations.

Because dynamic IPs can change regularly, it's recommended that you run this
utility periodically in the background to keep your records up-to-date.

Just add a line to your [crontab](http://en.wikipedia.org/wiki/Cron) and let
cron run it for you at a regular interval.

    # Every 30 minutes, update my Cloudflare records.
    */30 * * * * /path/to/cloudflare-ddns.py -z example.com

This example will update your records every 30 minutes. You'll want to be sure
that you insert the correct paths to reflect where the codebase is located.

If you want to learn more about the Cloudflare API, you can read on
[here](https://api.cloudflare.com/).

## Credits and Thanks
 - [Cloudflare](https://www.cloudflare.com/) for having an API and otherwise
   generally being cool.
 - [icanhazip.com](http://icanhazip.com/) for making grabbing your public IP
    from a script super easy.
 - [thatjpk](https://github.com/thatjpk/) for the initial releases of this project.

