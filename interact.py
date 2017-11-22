"""
Interact with an openstac V2 API to do some basic CRUD
@author: tonyth@kth.se
"""
from keystoneauth1.identity import v3

from keystoneauth1 import session
from keystoneclient.v3 import client


auth = v3.Password(
    auth_url="http://192.168.1.4/identity/v3", username="admin",
    password="password", project_name="demo", user_domain_id="default",
    project_domain_id="default"
)
sess = session.Session(auth=auth)
keystone = client.Client(session=sess)
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
from novaclient import client
nova = client.Client(2.1, session=sess)
flav = nova.flavors.find(name='m1.tiny')

# Now get the network
from neutronclient.v2_0 import client
neutron = client.Client(session=sess)

## Delete existing networks with test_net name
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
nics = [{"net-id": net['network']['id'], "v4-fixed-ip": '192.168.2.15'}]
nova.servers.create(name='api-test', image=image, flavor=flav, nics=nics)