#!/bin/bash
sudo vppctl create interface vmxnet3 0000:03:00.0 bind
sudo vppctl create interface vmxnet3 0000:04:00.0 bind
sudo vppctl create interface vmxnet3 0000:0b:00.0 bind
sudo vppctl create interface vmxnet3 0000:0c:00.0 bind
sudo vppctl create interface vmxnet3 0000:13:00.0 bind
sudo vppctl create interface vmxnet3 0000:1b:00.0 bind

