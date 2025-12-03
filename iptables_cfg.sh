# 1. CRITICAL: Change FORWARD policy to ACCEPT
sudo iptables -P FORWARD ACCEPT

# 2. Clear all NAT rules
sudo iptables -t nat -F
sudo iptables -t nat -X

# 3. Clear filter rules (but keep Docker chains)
sudo iptables -F INPUT
sudo iptables -F OUTPUT

# 4. Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf

# 5. Set up NAT rules for transparent proxy
sudo iptables -t nat -A PREROUTING -i pkt0 -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo iptables -t nat -A PREROUTING -i pkt0 -p tcp --dport 443 -j REDIRECT --to-port 8080
sudo iptables -t nat -A POSTROUTING -o pkt1 -j MASQUERADE

# 6. Allow forwarding between pkt0 and pkt1
sudo iptables -A FORWARD -i pkt0 -o pkt1 -j ACCEPT
sudo iptables -A FORWARD -i pkt1 -o pkt0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# 7. Allow local traffic to/from mitmproxy
sudo iptables -A INPUT -i pkt0 -j ACCEPT
sudo iptables -A OUTPUT -o pkt1 -j ACCEPT
