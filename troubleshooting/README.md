### 1. Server is not reachable or unable to connect
```
    ├── Ping the server by Hostname and IP Address
    │ ├── Hostname/IP Address is pingable
    │ │ ├── Issue might be on the client side as server is reachable
    │ ├── Hostname is not pingable but IP Address is pingable
    │ │ ├── Could be the DNS issue
    │ │ │ ├── check /etc/hosts
    │ │ │ ├── check /etc/resolv.conf
    │ │ │ ├── check /etc/nsswitch.conf
    │ │ │ ├── (Optional) DNS can also be defined in the
    /etc/sysconfig/network-scripts/ifcfg-<interface>
    │ ├── Hostname/IP Address both are not pingable
    │ │ ├── Check the other server on its same network to see if there is Network side
    access issue or other overall something bad
    │ │ │ ├── False: Issue is not overall network side but its with that host/server
    │ │ │ ├── True: Might be overall network side issue
    │ │ ├── Logged into server by Virtual Console, if the server is PoweredON. Check
    the uptime
    │ │ ├── Check if the server has the IP, and has UP status of Network interface
    │ │ │ ├── (Optional) Also check IP related information from
    /etc/sysconfig/network-scripts/ifcfg-<interface>
    │ │ ├── Ping the gateway, also check routes
    │ │ ├── Check Selinux, Firewall rules
    │ │ ├── Check physical cable conn
  
```

### 2 : Unable to connect to website or an application

```
    ├── Ping the server by Hostname and IP Address
    │ ├── False: Above Troublshooting Diagram "Server is not reachable or cannot
    connect"
    │ ├── True: Check the service availabilty by using telnet command with port
    │ │ ├── True: Service is running
    │ │ ├── False: Service is not reachable or running
    │ │ │ ├── Check the service status using systemctl or other command
    │ │ │ ├── Check the firewall/selinux
    │ │ │ ├── Check the service logs
    │ │ │ ├── Check the service configuration

```

### 3 : Unable to ssh as root or any other user.
```
    ├── Ping the server by Hostname and IP Address
    │ ├── False: Above Troublshooting Diagram "Server is not reachable or cannot
    connect"
    │ ├── True: Check the service availabilty by using telnet command with port
    │ │ ├── True: Service is running
    │ │ │ ├── Issue migh be on client side
    │ │ │ ├── User might be disabled, nologin shell, disabled root login and other
    configuration
    │ │ ├── False: Service is not reachable or running
    │ │ │ ├── Check the service status using systemctl or other command
    │ │ │ ├── Check the firewall/selinux
    │ │ │ ├── Check the service logs
    │ │ │ ├── Check the service configuration
```
### 4 : Disk Space is full issue or add/extend disk space
```
    ├── System Performance degradation detection
    │ ├── Application getting slow/unresponsive
    │ ├── Commands are not running (For Example: as / disk space is full)
    │ ├── Cannot do logging and other etc
    ├── Analyse the issue
    │ ├── df command to find the problematic filesystem space issue
    ├── Action
    │ ├── After finding the specific filesystem, use du command in that filesystem to get
    which files/directories are large
    │ ├── Compress/remove big files
    │ ├── Move the items to another partition/server
    │ ├── Check the health status of the disks using badblocks command (For Example:
    #badblocks -v /dev/sda)
    │ ├── Check which process is IO Bound (using iostat)
    │ ├── Create a link to file/dir
    ├── New disk addition
    │ ├── Simple partition
    │ │ ├── Add disk to VM
    │ │ ├── Check the new disk with df/lsblk command
    │ │ ├── fdisk to create partition. Better to have LVM partition
    │ │ ├── Create filesytem and mount it
    │ │ ├── fstab entry for persistent
    │ ├── LVM Partition
    │ │ ├── Add disk to VM
    │ │ ├── Check the new disk with df/lsblk command
    │ │ ├── fdisk to create LVM partition
    │ │ ├── PV, VG, LV
    │ │ ├── Create filesytem and mount it
    │ │ ├── fstab entry for persistent
    │ ├── Extend LVM partition
    │ │ ├── Add disk, and create LVM partition
    │ │ ├── Add LVM partition (PV) in existing VG
    │ │ ├── Extend LV and resize filesystem

```
### 5 : Filesystem corrupted

```
    ├── One of the error that cause the system unable to BOOT UP
    ├── Check /var/log/messages, dmesg and other log files
    ├── If we have a badsector logs, we have to run fsck
    │ ├── True:
    │ │ ├── reboot the system into resuce mode as booting it from CDROM by applying
    ISO
    │ │ ├── proceed with option 1, which mount the original root filesystem under
    /mnt/sysimage
    │ │ ├── edit fstab entries or create a new file with the help of blkid and reboot

```

### 6 : fstab file missing or bad entry

``` 
├── One of the error that cause the system unable to BOOT UP
├── Check /var/log/messages, dmesg and other log files
├── If we have a badsector logs, we have to run fsck
│ ├── True:
│ │ ├── reboot the system into resuce mode as booting it from CDROM by applying
ISO
│ │ ├── proceed with option 1, which mount the original root filesystem under
/mnt/sysimage
│ │ ├── edit fstab entries or create a new file with the help of blkid and reboot

```

### 7 : Can’t cd to the directory even if user has sudo privileges


``` 
    `├── Reasons and Resolution
    │ ├── Directory does not exist
    │ ├── Pathname conflict: relative vs absolute path
    │ ├── Parent directory permission/ownership
    │ ├── Doesn't have executable permission on target directory
    │ ├── Hidden directory`

```

### 8 : Can’t Create Links
``` 
├── Reasons and Resolution
│ ├── Target directory/File does not exist
│ ├── Pathname conflict: relative vs absolute path - (should be complete path)
│ ├── Parent directory permission/ownership
│ ├── Target file permission/ownership - (as there should be read permission)
│ ├── Hidden directory/file

```
### 9 : Running Out of Memory

```
    ├── Types
    │ ├── Cache (L1, L2, L3)
    │ ├── RAM
    │ │ ├── Usage
    │ │ │ ├── #free -h
    │ │ │ │ ├── Total (Total assigned memory)
    │ │ │ │ ├── Used (Total actual used memory)
    │ │ │ │ ├── Free (Actual free memory)
    │ │ │ │ ├── Shared (Shared Memory)
    │ │ │ │ ├── Buff/Cache (Pages cache memory)
    │ │ │ │ ├── Available (Memory can be freed)
    │ │ │ ├── /proc/meminfo
    │ │ │ │ ├── file active
    │ │ │ │ ├── file inactive
    │ │ │ │ ├── anon active
    │ │ │ │ ├── anon inactive
    │ ├── Swap (Virtual Memory)
    ├── Resolution
    │ ├── Identify the processes that are using high memory using top, htop, ps etc.
    │ ├── Check the OOM in logs and also check if there is a memory commitment in sysctl.conf
    │ ├── Kill or restart the process/service
    │ ├── prioritize the process using nice
    │ ├── Add/Extend the swap space
    │ ├── Add more physical more RAM
    └── ...

```
### 10 : Add/ Extend the Swap Space
```
├── Due to running out of memory, we would need to add more swap space
│ ├── Create a file with #dd, as it will reserve the blocks of disk for swap file
│ ├── Set permission 600 and give root ownership
│ ├── #mkswap
│ ├── Now Turned swap on #swapon
│ ├── fstab entry for persistent
└── ...

```

### 11 : Unable to Run Certain Commands
```
├── Troubleshooting and Resolution
│ ├── command
│ │ ├── Could be the system related command which non root user does not have
the access
│ │ ├── Could be the user defined script/command
│ ├── Troubleshooting
│ │ ├── permission/ownership of the command/script
│ │ ├── sudo permission
│ │ ├── absolute/relative path of command/script
│ │ ├── not defined in user $PATH variable
│ │ ├── command is not installed
│ │ ├── command library is missing or deleted

```
### 12 : System Unexpectedly reboot and process restart ?

```
    ├── Troubleshooting and Resolution
    │ ├── System reboot/crash reasons
    │ │ ├── CPU stress
    │ │ ├── RAM stress
    │ │ ├── Kernel fault
    │ │ ├── Hardware fault
    │ ├── Process restart
    │ │ ├── System reboot
    │ │ ├── Restart itself
    │ │ ├── Watchdog application
    │ │ │ ├── To prevent high stress on system resources
    │ │ │ ├── If application causing stress, so it will restart or terminate
    │ ├── Troubleshooting
    │ │ ├── After logged in, check the status by using commands like uptime, top,
    dmesg, journalctl, iostat -xz 1
    │ │ ├── syslog.log, boot.log, dmesg, messages.log etc
    │ │ ├── custom log path of applicatoin
    │ │ ├── if not completely accessible, so take the virutal console like from ILO,
    IDRAC etc
    │ │ ├── open a case and reach out a vendor
    └── ...

```
### 13 : Unable to get IP Address

```
├── IP Assignment Methods
│ ├── DHCP
│ │ ├── Fixed Allocation
│ │ ├── Dynamic Allocation
│ ├── Static
├── Troubleshooting
│ ├── check network setting from virtualization environment like VMware, VirtualBox
or etc
│ ├── check the IP address is assigned or not
│ ├── check the NIC status from host side using #lspci, #nmcli etc
│ ├── restart network service
└── 

```

### 14 : Backup and Restore File Permissions in Linux

``` 
├── Troubleshooting
│ ├── The best option is to create the ACL file of Dir/Files before changing the
permissions in bulk
│ │ ├── Create the acl file before changing the permission (or backup the file
permission): ~$ getfacl -R <dir> > permissions.acl
│ │ ├── Restore File Permissions: ~$ setfacl --restore=permissions.acl
│ ├── Restore from the VM Snapshot (But not always a good option for production)
│ ├── Rebuild the VM (this option is safe for future)
└── ...

```
### 