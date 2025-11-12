# Backup Plan Testing Drill

In case of an emergency, we need to test our backup plan.

## Test 1: Production Mac Studio Failover to Backup Mac Studio

1. Unplug the production Mac Studio's power cord.
2. Shut down the production Mac Studio.
3. Shut down production PCS docker containers.

Expected result:

-     The backup PCS should be automatically started by the pcs_docker_sync docker container.
- Monitor the MySQL VM inspect page or CMP to ensure people count data is still available in near real-time.

## Test 2: Backup Mac Studio Failover to Production Mac Studio

1. Unplug the backup Mac Studio's power cord.
2. Shut down the backup Mac Studio.
3. Shut down backup PCS docker containers.

Expected result:

- The production PCS should be automatically started by the pcs_docker_sync docker container.
- Monitor the MySQL VM inspect page or CMP to ensure people count data is still available in near real-time.



### Test 3: 2 Production Mac Studio and 1 backup Mac Studio

1. Unplug both production mac studio power cord/network cable.

Expected result:
- Backup mac studio should start all processes for the high priority production Mac Studio. The lower priority production Mac Studio do not have started backup at all.