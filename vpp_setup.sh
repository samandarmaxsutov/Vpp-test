sudo mkdir -p /dev/shm/vpp
sudo chown vpp:vpp /dev/shm/vpp 

sudo ifconfig  ens33 down
sudo ifconfig  ens37 down
sudo ifconfig  ens39 down
sudo ifconfig  ens256 down
sudo ifconfig  ens224 down
sudo ifconfig  ens193 down
sudo ifconfig  ens192 down
sudo ifconfig  ens161 down
sudo ifconfig  ens160 down


sudo systemctl restart vpp

sudo modprobe vfio-pci

echo Y | sudo tee /sys/module/vfio/parameters/enable_unsafe_noiommu_mode

