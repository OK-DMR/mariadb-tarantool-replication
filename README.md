# MySQL / MariaDB to Tarantool replication implementation

### Tested with:

  - Tarantool 1.10.3
  - MariaDB Server 10.1, 10.2 and 10.3

However it should be compatible with virtually every MariaDB version, or MySQL if you use correct python library.

## Installation

  - Install **Tarantool** with python bindings
    - for Debian
      - `apt-get install tarantool tarantool-python`
      - `pip3 install tarantool`
  - Install **Python Mysql Replication** python library
    - If you use MariaDB install https://github.com/smarek/python-mariadb-replication
    - If you use MySQL install https://github.com/noplay/python-mysql-replication

For **MariaDB**:

```
pip3 install -r requirements.txt

git clone --recursive https://github.com/smarek/python-mariadb-replication.git
cd python-mariadb-replication
python3 setup.py install
```

For **MySQL**:

```
pip3 install -r requirements.txt

pip3 install install mysql-replication
```

  - Install this project as a systemd unit service using `sudo install.sh`
  - Modify **/opt/MariaDBReplica/replica.yml**
  - Start the service `systemctl start replicatord.service`

*This can be also run by hand, without installing anything, just modify replica.yml and use `./replica.py`*

## Notes

  - This project is mostly compatible with official https://github.com/tarantool/mysql-tarantool-replication
    - We do not support function calls (insert_call, update_call, delete_call)
    - We support mapping columns by name from source to target ( no need to have exactly same columns in both locations )
    - We support addressing spaces by names, not by ID
  - Limitations
    - We do not type-check tarantool schema / fields / format, so if the DB data do not fit the Tarantool schema, it will fail terribly
    - We do not do `binlog_pos` or similar concept, MySQL tables are dumped on process start, and then the binlog is consumed, currently no binlog position resume is in place    

## Maintenance
*Listing commands just for completeness*

  - `systemctl status replicatord.service`
  - `systemctl stop replicatord.service`
  - `systemctl start replicatord.service`
  - `journalctl -xf -u replicatord.service` - use CTRL+C to stop the logs from comming
  - `journalctl -u replicatord.service`

