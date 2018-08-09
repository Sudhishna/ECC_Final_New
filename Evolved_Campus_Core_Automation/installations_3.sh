#!/bin/sh

# Accept the SSH Keys
ssh-keygen -R 192.168.122.30
ssh-keyscan -H 192.168.122.30 >> ~/.ssh/known_hosts

ssh-keygen -R 192.168.122.31
ssh-keyscan -H 192.168.122.31 >> ~/.ssh/known_hosts

ssh-keygen -R 192.168.122.32
ssh-keyscan -H 192.168.122.32 >> ~/.ssh/known_hosts

ssh-keygen -R 192.168.122.33
ssh-keyscan -H 192.168.122.33 >> ~/.ssh/known_hosts

