# Manually Start Backup PeopleCount System on Mac Studio 2 (192.168.secondary.ip)

## Stop Main PeopleCount Mac Studio (192.168.primary.ip) when the Mac Studio has issues/is down

### If possible, gracefully stop people count process on Mac Studio 1:

1. In people_count_crocoland/swift folder, run:
    ```bash
    ./stop_people_count.sh
    ```

2. Stop all docker containers on Mac Studio 1 if possible.

### If graceful stop is not possible:
```bash
killall python
```
Please note force kill process would lead to people_count_database.db file corruption sometimes. Sometimes, 'sudo reboot' would lead to the Docker containers failed to start.


## Start backup people count system on Mac Studio 2:

1. VNC/SSH to Mac Studio 2 (192.168.secondary.ip)

2. Start people_count_op docker stack on Mac Studio 2

3. Copy production mysql sync docker container config file to Mac Studio 2 (if needed):
    ```bash
    docker cp mysql_sync/config_db_sync.json_production people_count_op-sync_mysql-1:/app/config_db_sync.json
    docker restart people_count_op-sync_mysql-1
    ```

4. In ~/people_count_op/swift folder, run:
    ```bash
    conda activate pcs
    ./start_people_count.sh
    ```


Then check http://192.168.secondary.ip:5000/ to see if people count working
Check docker logs of people_count_op-sync_mysql-1, it should be syncing data to production mysql database without error.