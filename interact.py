"""
Interact with an openstac V2 API to do some basic CRUD
@author: tonyth@kth.se
"""
import argparse
from keystoneauth1.identity import v3

from keystoneauth1 import session
from keystoneclient.v3 import client as keystoneclient
from novaclient import client as novaclient


def execute(
        auth_url=None, username=None, password=None, instance_ip_address=None
):
    auth = v3.Password(
        auth_url=auth_url, username=username,
        password=password, project_name="demo", user_domain_id="default",
        project_domain_id="default"
    )
    if auth:
        print('Connection success')
    sess = session.Session(auth=auth)
    keystone = keystoneclient.Client(session=sess)
    print(keystone.projects.list())

    # now check out images from glance
    from glanceclient import Client
    glance = Client('2', session=sess)

    image_ids = []
    for image in glance.images.list():
        image_ids.append(image.id)

    print('{0} Images found'.format(len(image_ids)))
    image = image_ids[0]

    # now connect to nova client

    nova = novaclient.Client(2.1, session=sess)
    flav = nova.flavors.find(name='m1.tiny')

    # Now get the network
    from neutronclient.v2_0 import client
    neutron = client.Client(session=sess)

    # Delete existing networks with test_net name
    for serv in nova.servers.list():
        serv.delete()

    subnets = neutron.list_subnets()
    for sub in subnets['subnets']:
        if sub['name'] == 'test_sub':
            try:
                neutron.remove_interface_router(
                    neutron.list_routers()['routers'][0]['id'],
                    body={
                        'subnet_id': sub['id']
                    }
                )
            except:
                # This can happen when it was deleted already
                pass
            neutron.delete_subnet(sub['id'])

    networks = neutron.list_networks()
    for net in networks['networks']:
        if net['name'] == 'test_net':
            neutron.delete_network(net['id'])

    net = neutron.create_network(
        body={"network": {"name": "test_net", "admin_state_up": True}}
    )

    sub = neutron.create_subnet(
        body={
            'subnet': {
                'name': 'test_sub', 'network_id': net['network']['id'],
                'ip_version': 4, 'cidr': '192.168.2.1/24',
                'enable_dhcp': True
            }
        }
    )
    neutron.add_interface_router(
        neutron.list_routers()['routers'][0]['id'],
        body={
            'subnet_id': sub['subnet']['id']
        }
    )
    nics = [
        {
            'net-id': net['network']['id'],
            'v4-fixed-ip': '{0}'.format(instance_ip_address)
        }
    ]
    instance = nova.servers.create(
        name='api-test', image=image, flavor=flav, nics=nics
    )
    if instance:
        print('Created: {0}'.format(instance))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ip_address', '-ip', action='store', help='IP address of machine to '
                                                    'build'
    )
    parser.add_argument(
        '--auth_url', '-auth', action='store', help='Identity Auth URL',
    )
    parser.add_argument(
        '--username', '-u', action='store', help='Username to log in'
    )
    parser.add_argument(
        '--password', '-p', action='store', help='Password to log in'
    )
    arguments = parser.parse_args()
    print('Creating: {0}'.format(arguments.ip_address))

    execute(
        auth_url=arguments.auth_url, username=arguments.username,
        password=arguments.password, instance_ip_address=arguments.ip_address
    )