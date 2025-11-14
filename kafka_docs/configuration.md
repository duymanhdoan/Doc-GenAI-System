# Cấu hình và Tối ưu Kafka

## Broker Configuration

### Server Basics

```properties
############################# Server Basics #############################

# ID của broker trong cluster (phải unique)
broker.id=0

# Listeners - các endpoint mà broker lắng nghe
listeners=PLAINTEXT://localhost:9092

# Advertised listeners - địa chỉ clients sẽ kết nối
advertised.listeners=PLAINTEXT://localhost:9092

# Số lượng threads xử lý network requests
num.network.threads=3

# Số lượng threads xử lý I/O requests
num.io.threads=8

# Send buffer cho socket connections
socket.send.buffer.bytes=102400

# Receive buffer cho socket connections
socket.receive.buffer.bytes=102400

# Max size của request được phép
socket.request.max.bytes=104857600
```

### Log Basics

```properties
############################# Log Basics #############################

# Thư mục lưu trữ log data
log.dirs=/var/lib/kafka/logs

# Default số partitions cho mỗi topic
num.partitions=1

# Số threads cho log recovery và flushing
num.recovery.threads.per.data.dir=1
```

### Replication

```properties
############################# Replication #############################

# Default replication factor cho auto-created topics
default.replication.factor=3

# Min số ISR để được write
min.insync.replicas=2

# Timeout cho replica lag
replica.lag.time.max.ms=30000

# Max số bytes replica fetch từ leader mỗi request
replica.fetch.max.bytes=1048576

# Fetch wait time
replica.fetch.wait.max.ms=500

# Socket timeout cho replica
replica.socket.timeout.ms=30000

# Buffer size cho replica
replica.socket.receive.buffer.bytes=65536
```

### Log Retention

```properties
############################# Log Retention #############################

# Thời gian giữ log (hours)
log.retention.hours=168

# Thời gian giữ log (minutes) - cao hơn hours
log.retention.minutes=10080

# Thời gian giữ log (ms) - cao nhất
log.retention.ms=604800000

# Max size của log segment file
log.segment.bytes=1073741824

# Interval kiểm tra log segments để xóa
log.retention.check.interval.ms=300000

# Max size của log (per partition) trước khi xóa messages cũ
log.retention.bytes=1073741824

# Cleanup policy: delete hoặc compact
log.cleanup.policy=delete
```

### Log Compaction

```properties
############################# Log Compaction #############################

# Enable log compaction
log.cleanup.policy=compact

# Min ratio dirty log / total log để trigger compaction
log.cleaner.min.compaction.lag.ms=0

# Max time message sẽ remain uncompacted
log.cleaner.max.compaction.lag.ms=9223372036854775807

# Số threads cho log cleaning
log.cleaner.threads=1

# I/O buffer size cho cleaning
log.cleaner.io.buffer.size=524288

# Dedupe buffer size
log.cleaner.dedupe.buffer.size=134217728
```

### ZooKeeper

```properties
############################# ZooKeeper #############################

# ZooKeeper connection string
zookeeper.connect=localhost:2181

# Timeout cho ZooKeeper session
zookeeper.session.timeout.ms=18000

# Connection timeout
zookeeper.connection.timeout.ms=18000
```

### Group Coordinator

```properties
############################# Group Coordinator #############################

# Delay time trước khi rebalance
group.initial.rebalance.delay.ms=3000

# Min session timeout
group.min.session.timeout.ms=6000

# Max session timeout
group.max.session.timeout.ms=1800000
```

## Producer Configuration

### Required Configuration

```properties
# Kafka brokers
bootstrap.servers=localhost:9092

# Key serializer
key.serializer=org.apache.kafka.common.serialization.StringSerializer

# Value serializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer
```

### Important Configuration

```properties
############################# Producer Configuration #############################

# Acknowledgment mode: 0, 1, all
acks=all

# Retry count
retries=2147483647

# Retry backoff
retry.backoff.ms=100

# Max in-flight requests
max.in.flight.requests.per.connection=5

# Enable idempotence
enable.idempotence=true

# Compression type: none, gzip, snappy, lz4, zstd
compression.type=snappy

# Batch size (bytes)
batch.size=16384

# Linger time (ms)
linger.ms=0

# Buffer memory (bytes)
buffer.memory=33554432

# Max request size
max.request.size=1048576

# Request timeout
request.timeout.ms=30000

# Delivery timeout
delivery.timeout.ms=120000

# Metadata max age
metadata.max.age.ms=300000

# Max block time
max.block.ms=60000
```

### Idempotent Producer

```properties
# Enable idempotence (exactly-once per partition)
enable.idempotence=true
acks=all
retries=2147483647
max.in.flight.requests.per.connection=5
```

### Transactional Producer

```properties
# Transaction ID
transactional.id=my-transactional-id

# Transaction timeout
transaction.timeout.ms=60000

# Enable idempotence (required)
enable.idempotence=true
```

## Consumer Configuration

### Required Configuration

```properties
# Kafka brokers
bootstrap.servers=localhost:9092

# Consumer group ID
group.id=my-consumer-group

# Key deserializer
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer

# Value deserializer
value.deserializer=org.apache.kafka.common.serialization.StringDeserializer
```

### Important Configuration

```properties
############################# Consumer Configuration #############################

# Auto offset reset: earliest, latest, none
auto.offset.reset=latest

# Enable auto commit
enable.auto.commit=true

# Auto commit interval
auto.commit.interval.ms=5000

# Session timeout
session.timeout.ms=45000

# Heartbeat interval
heartbeat.interval.ms=3000

# Max poll interval
max.poll.interval.ms=300000

# Max poll records
max.poll.records=500

# Fetch min bytes
fetch.min.bytes=1

# Fetch max wait
fetch.max.wait.ms=500

# Max partition fetch bytes
max.partition.fetch.bytes=1048576

# Check CRC
check.crcs=true

# Isolation level: read_uncommitted, read_committed
isolation.level=read_uncommitted

# Allow auto create topics
allow.auto.create.topics=true
```

### Consumer Group Configuration

```properties
# Static membership
group.instance.id=consumer-1

# Partition assignment strategy
partition.assignment.strategy=org.apache.kafka.clients.consumer.RangeAssignor,\
  org.apache.kafka.clients.consumer.CooperativeStickyAssignor
```

## Performance Tuning

### Broker Performance

```properties
############################# Broker Performance #############################

# Increase network threads
num.network.threads=8

# Increase I/O threads
num.io.threads=16

# Increase socket buffers
socket.send.buffer.bytes=1048576
socket.receive.buffer.bytes=1048576

# Increase queued requests
queued.max.requests=500

# Log flush interval (messages)
log.flush.interval.messages=10000

# Log flush interval (ms)
log.flush.interval.ms=1000

# Increase segment size
log.segment.bytes=1073741824

# Background threads
background.threads=10

# Compression
compression.type=producer
```

### Producer Performance

```properties
############################# Producer Performance #############################

# Increase batch size
batch.size=65536

# Increase linger time
linger.ms=10

# Increase buffer memory
buffer.memory=67108864

# Compression
compression.type=lz4

# Max in-flight
max.in.flight.requests.per.connection=5

# Acks
acks=1
```

### Consumer Performance

```properties
############################# Consumer Performance #############################

# Increase fetch min bytes
fetch.min.bytes=50000

# Increase max poll records
max.poll.records=1000

# Increase partition fetch bytes
max.partition.fetch.bytes=2097152

# Decrease fetch max wait
fetch.max.wait.ms=100

# Multiple consumer threads
# (Deploy multiple consumer instances)
```

## Memory Configuration

### Broker Memory

```bash
# Set in kafka-server-start.sh
export KAFKA_HEAP_OPTS="-Xmx6G -Xms6G"

# GC options
export KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=20 \
  -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16M \
  -XX:MinMetaspaceFreeRatio=50 -XX:MaxMetaspaceFreeRatio=80"
```

### Producer/Consumer Memory

```bash
# Producer
export KAFKA_HEAP_OPTS="-Xmx1G -Xms1G"

# Consumer
export KAFKA_HEAP_OPTS="-Xmx2G -Xms2G"
```

## Topic Configuration

### Create với Configuration

```bash
kafka-topics.sh --create \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --partitions 6 \
  --replication-factor 3 \
  --config retention.ms=86400000 \
  --config segment.ms=3600000 \
  --config compression.type=snappy \
  --config min.insync.replicas=2 \
  --config max.message.bytes=1048576 \
  --config cleanup.policy=delete
```

### Topic-level Configs

```properties
# Retention
retention.ms=604800000
retention.bytes=1073741824

# Segment
segment.ms=604800000
segment.bytes=1073741824

# Cleanup
cleanup.policy=delete
delete.retention.ms=86400000

# Compression
compression.type=producer
min.compaction.lag.ms=0
max.compaction.lag.ms=9223372036854775807

# Message size
max.message.bytes=1048576
min.insync.replicas=2

# Flush
flush.messages=9223372036854775807
flush.ms=9223372036854775807

# Indexing
segment.index.bytes=10485760
segment.jitter.ms=0

# Preallocate
preallocate=false

# Unclean leader election
unclean.leader.election.enable=false
```

## Cluster Configuration

### Multi-Broker Setup

**broker-1.properties:**
```properties
broker.id=1
listeners=PLAINTEXT://broker1:9092
log.dirs=/var/lib/kafka/logs-1
```

**broker-2.properties:**
```properties
broker.id=2
listeners=PLAINTEXT://broker2:9092
log.dirs=/var/lib/kafka/logs-2
```

**broker-3.properties:**
```properties
broker.id=3
listeners=PLAINTEXT://broker3:9092
log.dirs=/var/lib/kafka/logs-3
```

### Rack Awareness

```properties
# Assign broker to rack
broker.rack=rack1

# Replica placement
replica.selector.class=org.apache.kafka.common.replica.RackAwareReplicaSelector
```

## KRaft Configuration

### Controller Properties

```properties
# Node ID
node.id=1

# Process roles
process.roles=controller

# Controller quorum voters
controller.quorum.voters=1@controller1:9093,2@controller2:9093,3@controller3:9093

# Listeners
listeners=CONTROLLER://localhost:9093
controller.listener.names=CONTROLLER

# Log dirs
log.dirs=/var/lib/kafka/metadata-logs
```

### Combined Controller/Broker

```properties
# Node ID
node.id=1

# Both roles
process.roles=broker,controller

# Listeners
listeners=PLAINTEXT://localhost:9092,CONTROLLER://localhost:9093
advertised.listeners=PLAINTEXT://localhost:9092

# Controller config
controller.quorum.voters=1@localhost:9093,2@localhost:9094,3@localhost:9095
controller.listener.names=CONTROLLER

# Listener security
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT

# Log dirs
log.dirs=/var/lib/kafka/kraft-combined-logs
```

## Monitoring Configuration

### JMX Configuration

```bash
# Enable JMX
export KAFKA_JMX_OPTS="-Dcom.sun.management.jmxremote \
  -Dcom.sun.management.jmxremote.authenticate=false \
  -Dcom.sun.management.jmxremote.ssl=false \
  -Djava.rmi.server.hostname=kafka-broker \
  -Dcom.sun.management.jmxremote.port=9999"
```

### Metrics Reporters

```properties
# Metrics reporters
metric.reporters=

# Metrics collection interval
metrics.sample.window.ms=30000

# Number of samples
metrics.num.samples=2

# Metrics recording level: INFO, DEBUG
metrics.recording.level=INFO
```

## Best Practices

### Production Configuration

**Broker:**
```properties
# Replication
default.replication.factor=3
min.insync.replicas=2
unclean.leader.election.enable=false

# Log retention
log.retention.hours=168
log.segment.bytes=1073741824

# Performance
num.network.threads=8
num.io.threads=16

# Reliability
auto.create.topics.enable=false
delete.topic.enable=true
```

**Producer:**
```properties
acks=all
retries=2147483647
max.in.flight.requests.per.connection=5
enable.idempotence=true
compression.type=snappy
batch.size=32768
linger.ms=10
```

**Consumer:**
```properties
enable.auto.commit=false
auto.offset.reset=earliest
max.poll.records=500
session.timeout.ms=30000
heartbeat.interval.ms=3000
```

### Development Configuration

**Broker:**
```properties
default.replication.factor=1
min.insync.replicas=1
auto.create.topics.enable=true
```

**Producer:**
```properties
acks=1
retries=0
compression.type=none
```

**Consumer:**
```properties
enable.auto.commit=true
auto.offset.reset=latest
```

## Configuration Management

### Dynamic Configuration

```bash
# Alter broker config
kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type brokers \
  --entity-name 0 \
  --alter \
  --add-config log.retention.hours=168

# Alter topic config
kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name my-topic \
  --alter \
  --add-config retention.ms=86400000

# Describe config
kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name my-topic \
  --describe

# Delete config
kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name my-topic \
  --alter \
  --delete-config retention.ms
```

## Troubleshooting Configuration

### Common Issues

**Under-replicated Partitions:**
```properties
# Increase replica fetch threads
num.replica.fetchers=4

# Increase replica lag time
replica.lag.time.max.ms=30000
```

**High Latency:**
```properties
# Reduce batch size
batch.size=8192

# Reduce linger time
linger.ms=0

# Reduce fetch wait
fetch.max.wait.ms=100
```

**Low Throughput:**
```properties
# Increase batch size
batch.size=65536

# Increase linger time
linger.ms=20

# Enable compression
compression.type=lz4

# Increase buffer
buffer.memory=67108864
```
