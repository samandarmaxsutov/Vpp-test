from vpp_connection import get_vpp_connection

v = get_vpp_connection()
if not v:
    raise RuntimeError("Not connected to VPP")

# NAT44-EI configuration parameters
inside_vrf = 0
outside_vrf = 0
max_users = 1024
user_memory = 0           # 0 = default
max_sessions = 4096
session_memory = 0        # 0 = default
user_sessions = 100
enable = True             # True = enable, False = disable
flags = 0                 # e.g., NAT44_EI_IS_CONNECTION_TRACKING

# Enable the plugin
v.api.nat44_ei_plugin_enable_disable(
    inside_vrf=inside_vrf,
    outside_vrf=outside_vrf,
    users=max_users,
    user_memory=user_memory,
    sessions=max_sessions,
    session_memory=session_memory,
    user_sessions=user_sessions,
    enable=enable,
    flags=flags
)

print("NAT44-EI plugin enabled via API")
