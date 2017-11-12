#! /usr/bin/env python
import requests
import yaml
from os import path
from sys import exit
import logging
import argparse
from subprocess import Popen, PIPE
from glob import glob
import time

# CLI
parser = argparse.ArgumentParser('cloudflare-ddns.py')
parser.add_argument('-z', '--zone', dest="zone", action="append", help="Zone name")
parser.add_argument('-l', '--logs', dest="logs", help="Logs folder")
parser.add_argument('-da', '--daemon', dest="daemon", action="store_true", help="Daemon flag")
args = parser.parse_args()

# Logging
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

# Cloudflare API
API_HEADERS = {}
API_ENDPOINT = 'https://api.cloudflare.com/client/v4/'

# Cached IP addresses
IP_ADDRESSES = {
    4: None,
    6: None
}


# Start the client
def main():
    # Preliminary checks
    if not args.zone:
        LOGGER.critical("Please specify a zone or folder name")
        return

    # add paths of every yml file
    config_paths = []
    for zone in set(args.zone):
        if path.isdir(zone):
            config_paths += glob(path.join(zone, '*.yml'))
            config_paths += glob(path.join(zone, '*.yaml'))

        elif path.isfile(zone):
            config_paths += [zone]

        else:
            LOGGER.warning("Config file not found: '{}'".format(zone))

    # use every yml file
    LOGGER.debug('{} zones found to process'.format(len(config_paths)))
    for config_path in config_paths:
        if not path.isfile(config_path):
            LOGGER.critical("Zone '{}' not found".format(path.basename(zone)))
            return

        # Read config file
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            cf_api_key = config.get('cf_api_key')
            cf_email = config.get('cf_email')
            cf_zone = config.get('cf_zone')
            cf_records = config.get('cf_records')
            cf_resolving_method = config.get('cf_resolving_method', 'http')
            cf_logging_level = config.get('cf_logging_level', 'INFO')

        # Create API authentication headers
        global API_HEADERS
        API_HEADERS = {
            'X-Auth-Key': cf_api_key,
            'X-Auth-Email': cf_email
        }

        # Get zone informations
        payload = {
            'name': cf_zone
        }
        r = requests.get(API_ENDPOINT + 'zones', headers=API_HEADERS, params=payload)
        data = r.json().get('result')
        if not data:
            LOGGER.critical("The zone '{}' was not found on your account".format(cf_zone))
            return
        cf_zone_uuid = data[0]['id']
        cf_zone_name = data[0]['name']

        # Logging
        if args.logs and path.isdir(args.logs):
            fh = logging.FileHandler(path.join(args.logs, cf_zone_name + '.log'))
            fh.setFormatter(formatter)
            LOGGER.addHandler(fh)

        # Get (all) zone records
        cf_zone_records = get_zone_records(cf_zone_uuid)

        # Update each record
        for records in cf_records:
            for record_name in records:
                local_record = records[record_name]

                # Set logging level
                log_level = local_record.get('log', 'INFO')
                LOGGER.setLevel(logging.getLevelName(log_level))

                # Format record name
                if record_name == '@':
                    name = cf_zone_name
                else:
                    name = record_name + '.' + cf_zone_name

                # Try to find the record by its name and type
                zone_record = None
                for record in cf_zone_records:
                    if record.get('name') == name and record.get('type') == local_record.get('type'):
                        zone_record = record

                # Update the record if found
                if not zone_record:
                    LOGGER.error("The record '{}' ({}) was not found".format(name, local_record.get('type')))
                    continue
                update_record(zone_record, local_record, cf_resolving_method)


# Get all records from zone
def get_zone_records(zone_uuid):
    records = []
    current_page = 0
    total_pages = 1

    # Get all records
    while current_page != total_pages:
        current_page += 1
        payload = {
            'page': current_page,
            'per_page': 50
        }
        r = requests.get(API_ENDPOINT + 'zones/' + zone_uuid + '/dns_records', headers=API_HEADERS, params=payload)
        data = r.json().get('result')
        if not data:
            continue
        records.extend(data)

        # Update total pages
        data = r.json().get('result_info')
        total_pages = data.get('total_pages', 1)

    # Return all records
    return records


# Update a record
def update_record(zone_record, local_record, resolving_method):
    ip = get_ip(resolving_method, local_record.get('type'))
    name = zone_record.get('name')
    record_type = zone_record.get('type')
    ttl = local_record.get('ttl', zone_record.get('ttl'))
    proxied = local_record.get('proxied', zone_record.get('proxied'))

    # Check if the TTL is valid
    if proxied:
        ttl = 1
    elif not 120 <= ttl <= 2147483647 and not ttl == 1:
        LOGGER.error("Skipping record '{}' ({}) because of bad TTL".format(name, record_type))
        return

    # Check if the record needs to be updated
    if zone_record.get('content') == ip and zone_record.get('ttl') == ttl and zone_record.get('proxied') == proxied:
        LOGGER.info("The record '{}' ({}) is already up to date".format(name, record_type))
        return

    # Update the record
    payload = {
        'ttl': ttl,
        'name': name,
        'type': record_type,
        'content': ip,
        'proxied': proxied
    }
    r = requests.put(API_ENDPOINT + 'zones/' + zone_record.get('zone_id') + '/dns_records/' + zone_record.get('id'), headers=API_HEADERS, json=payload)
    success = r.json().get('success')
    if not success:
        LOGGER.critical("An error occured whilst trying to update '{}' ({}) record".format(name, record_type))
        return
    LOGGER.info("The record '{}' ({}) has been updated successfully".format(name, record_type))


# Resolve the server's IP
def get_ip(method, record_type):
    v = (record_type == 'AAAA' and 6 or 4)

    # Return cached if possible
    if IP_ADDRESSES[v]:
        return IP_ADDRESSES[v]

    # Dig resolving method
    if method == 'dig':
        resolvers = {
            4: 'resolver1.opendns.com',
            6: 'resolver1.ipv6-sandbox.opendns.com'
        }
        p = Popen(['dig', '+short', 'myip.opendns.com', record_type, '@' + resolvers[v], '-{}'.format(v)], stdin=PIPE, stderr=PIPE, stdout=PIPE)
        output, err = p.communicate()
        public_ip = output.decode().rstrip()

    # HTTP resolving method
    elif method == 'http':
        r = requests.get('https://ipv{}.icanhazip.com'.format(v))
        public_ip = r.text.rstrip()

    # Save the IP address in cache
    IP_ADDRESSES[v] = public_ip
    return public_ip


# Main
if __name__ == '__main__':
    if args.daemon:
        LOGGER.info('#' * 39)
        LOGGER.info('Daemon running, press "CTRL+c" to abort')
        LOGGER.info('or stop the Docker container.')
        LOGGER.info('#' * 39)
        while True:
            try:
                main()

            except Exception as e:
                LOGGER.exception(e)

            # update ddns records every 5 minutes
            time.sleep(5 * 60)
    else:
        main()
