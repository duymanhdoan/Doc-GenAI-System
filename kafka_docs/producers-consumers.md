# Producers và Consumers trong Apache Kafka

## Kafka Producers

### Tổng quan

**Producer** là client application gửi (publish) messages đến Kafka topics.

### Producer Architecture

```
┌─────────────────────────────────────────┐
│         Producer Application            │
│  ┌───────────────────────────────────┐  │
│  │  1. Create ProducerRecord         │  │
│  │  2. Serialize Key & Value         │  │
│  │  3. Determine Partition           │  │
│  │  4. Add to Batch                  │  │
│  │  5. Send to Broker                │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  ↓
         ┌────────────────┐
         │ Kafka Cluster  │
         └────────────────┘
```

### Producer Configuration

#### Basic Configuration

```java
Properties props = new Properties();

// Required configurations
props.put("bootstrap.servers", "localhost:9092,localhost:9093,localhost:9094");
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");

// Create producer
KafkaProducer<String, String> producer = new KafkaProducer<>(props);
```

#### Important Configurations

```properties
# Acknowledgments
acks=all                    # all, 1, 0
retries=3                   # Số lần retry
max.in.flight.requests.per.connection=5

# Batching
batch.size=16384           # Bytes
linger.ms=10               # Chờ để batch

# Compression
compression.type=snappy    # none, gzip, snappy, lz4, zstd

# Idempotence
enable.idempotence=true    # Đảm bảo exactly-once

# Timeout
request.timeout.ms=30000
delivery.timeout.ms=120000
```

### Sending Messages

#### 1. Fire-and-Forget

```java
ProducerRecord<String, String> record =
    new ProducerRecord<>("topic", "key", "value");

producer.send(record);  // Không chờ response
```

**Đặc điểm:**
- Fastest
- Có thể mất messages
- Dùng cho non-critical data

#### 2. Synchronous Send

```java
ProducerRecord<String, String> record =
    new ProducerRecord<>("topic", "key", "value");

try {
    RecordMetadata metadata = producer.send(record).get();
    System.out.printf("Sent to partition %d with offset %d%n",
        metadata.partition(), metadata.offset());
} catch (Exception e) {
    e.printStackTrace();
}
```

**Đặc điểm:**
- Chờ acknowledgment
- Slower (blocking)
- Biết chắc message đã gửi thành công

#### 3. Asynchronous Send with Callback

```java
ProducerRecord<String, String> record =
    new ProducerRecord<>("topic", "key", "value");

producer.send(record, new Callback() {
    @Override
    public void onCompletion(RecordMetadata metadata, Exception exception) {
        if (exception != null) {
            System.err.println("Error sending message: " + exception);
        } else {
            System.out.printf("Message sent to partition %d with offset %d%n",
                metadata.partition(), metadata.offset());
        }
    }
});
```

**Đặc điểm:**
- Non-blocking
- Callback xử lý kết quả
- Best practice cho production

### Partitioning Strategies

#### 1. Default Partitioner (với key)

```java
// Messages với cùng key vào cùng partition
ProducerRecord<String, String> record =
    new ProducerRecord<>("users", "user-123", userData);
```

**Cách hoạt động:**
```
hash(key) % number_of_partitions = partition_id
```

#### 2. Round-Robin (không có key)

```java
// Phân phối đều qua các partitions
ProducerRecord<String, String> record =
    new ProducerRecord<>("logs", logData);
```

#### 3. Custom Partitioner

```java
public class RegionPartitioner implements Partitioner {
    @Override
    public int partition(String topic, Object key, byte[] keyBytes,
                        Object value, byte[] valueBytes, Cluster cluster) {
        String keyStr = (String) key;

        if (keyStr.startsWith("US")) return 0;
        if (keyStr.startsWith("EU")) return 1;
        if (keyStr.startsWith("ASIA")) return 2;

        return 3; // Default partition
    }

    @Override
    public void close() {}

    @Override
    public void configure(Map<String, ?> configs) {}
}

// Sử dụng
props.put("partitioner.class", "com.example.RegionPartitioner");
```

### Producer Best Practices

#### 1. Idempotent Producer

```properties
enable.idempotence=true
acks=all
retries=Integer.MAX_VALUE
max.in.flight.requests.per.connection=5
```

**Lợi ích:**
- Tránh duplicate messages
- Đảm bảo ordering trong partition
- Exactly-once semantics

#### 2. Batching và Compression

```properties
# Tăng batch size
batch.size=32768
linger.ms=20

# Enable compression
compression.type=snappy
```

#### 3. Error Handling

```java
Properties props = new Properties();
props.put("retries", 3);
props.put("retry.backoff.ms", 1000);

producer.send(record, (metadata, exception) -> {
    if (exception != null) {
        if (exception instanceof RetriableException) {
            // Kafka sẽ tự retry
            logger.warn("Retriable error: {}", exception.getMessage());
        } else {
            // Non-retriable error - cần xử lý
            logger.error("Fatal error: {}", exception.getMessage());
            // Log to dead letter queue, alert, etc.
        }
    }
});
```

#### 4. Resource Management

```java
// Luôn close producer
try (KafkaProducer<String, String> producer = new KafkaProducer<>(props)) {
    producer.send(record);
} // Auto-close
```

---

## Kafka Consumers

### Tổng quan

**Consumer** là client application đọc (consume) messages từ Kafka topics.

### Consumer Architecture

```
┌─────────────────────────────────┐
│      Kafka Cluster              │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│    Consumer Application         │
│  ┌──────────────────────────┐   │
│  │  1. Poll messages        │   │
│  │  2. Deserialize          │   │
│  │  3. Process              │   │
│  │  4. Commit offset        │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

### Consumer Configuration

#### Basic Configuration

```java
Properties props = new Properties();

// Required
props.put("bootstrap.servers", "localhost:9092");
props.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
props.put("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
props.put("group.id", "my-consumer-group");

// Create consumer
KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
```

#### Important Configurations

```properties
# Consumer Group
group.id=my-group
group.instance.id=consumer-1  # Static membership

# Offset Management
enable.auto.commit=true
auto.commit.interval.ms=5000
auto.offset.reset=earliest    # earliest, latest, none

# Fetch
fetch.min.bytes=1
fetch.max.wait.ms=500
max.partition.fetch.bytes=1048576

# Session
session.timeout.ms=10000
heartbeat.interval.ms=3000
max.poll.interval.ms=300000
max.poll.records=500
```

### Subscribing to Topics

#### 1. Subscribe to Topics

```java
// Subscribe to single topic
consumer.subscribe(Collections.singletonList("orders"));

// Subscribe to multiple topics
consumer.subscribe(Arrays.asList("orders", "payments", "users"));

// Subscribe with pattern
consumer.subscribe(Pattern.compile("event-.*"));
```

#### 2. Assign Specific Partitions

```java
// Manual partition assignment
TopicPartition partition0 = new TopicPartition("orders", 0);
TopicPartition partition1 = new TopicPartition("orders", 1);

consumer.assign(Arrays.asList(partition0, partition1));
```

### Consuming Messages

#### Basic Poll Loop

```java
consumer.subscribe(Arrays.asList("orders"));

try {
    while (true) {
        ConsumerRecords<String, String> records =
            consumer.poll(Duration.ofMillis(100));

        for (ConsumerRecord<String, String> record : records) {
            System.out.printf("Topic: %s, Partition: %d, Offset: %d, Key: %s, Value: %s%n",
                record.topic(), record.partition(), record.offset(),
                record.key(), record.value());
        }
    }
} finally {
    consumer.close();
}
```

#### Processing by Partition

```java
ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

for (TopicPartition partition : records.partitions()) {
    List<ConsumerRecord<String, String>> partitionRecords =
        records.records(partition);

    for (ConsumerRecord<String, String> record : partitionRecords) {
        processRecord(record);
    }

    // Commit per partition
    long lastOffset = partitionRecords.get(partitionRecords.size() - 1).offset();
    consumer.commitSync(Collections.singletonMap(
        partition, new OffsetAndMetadata(lastOffset + 1)
    ));
}
```

### Offset Management

#### 1. Auto Commit (Default)

```java
props.put("enable.auto.commit", "true");
props.put("auto.commit.interval.ms", "5000");

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
    for (ConsumerRecord<String, String> record : records) {
        processRecord(record);
    }
    // Offsets tự động commit mỗi 5 giây
}
```

**Rủi ro:** Có thể mất messages nếu consumer crash trước khi commit.

#### 2. Manual Commit - Synchronous

```java
props.put("enable.auto.commit", "false");

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

    for (ConsumerRecord<String, String> record : records) {
        processRecord(record);
    }

    try {
        consumer.commitSync();  // Block until commit completes
    } catch (CommitFailedException e) {
        logger.error("Commit failed", e);
    }
}
```

#### 3. Manual Commit - Asynchronous

```java
props.put("enable.auto.commit", "false");

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

    for (ConsumerRecord<String, String> record : records) {
        processRecord(record);
    }

    consumer.commitAsync((offsets, exception) -> {
        if (exception != null) {
            logger.error("Commit failed for offsets {}", offsets, exception);
        }
    });
}
```

#### 4. Commit Specific Offset

```java
Map<TopicPartition, OffsetAndMetadata> currentOffsets = new HashMap<>();

for (ConsumerRecord<String, String> record : records) {
    processRecord(record);

    currentOffsets.put(
        new TopicPartition(record.topic(), record.partition()),
        new OffsetAndMetadata(record.offset() + 1, "metadata")
    );

    if (currentOffsets.size() >= 100) {
        consumer.commitSync(currentOffsets);
        currentOffsets.clear();
    }
}
```

### Consumer Groups

#### Group Coordination

```
Topic: orders (6 partitions)
Consumer Group: order-processors

Initial state (3 consumers):
Consumer 1: Partitions 0, 1
Consumer 2: Partitions 2, 3
Consumer 3: Partitions 4, 5

After Consumer 2 leaves (rebalance):
Consumer 1: Partitions 0, 1, 2
Consumer 3: Partitions 3, 4, 5
```

#### Rebalance Listener

```java
consumer.subscribe(Arrays.asList("orders"), new ConsumerRebalanceListener() {
    @Override
    public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
        // Commit offsets trước khi partitions bị revoke
        consumer.commitSync(currentOffsets);
        System.out.println("Partitions revoked: " + partitions);
    }

    @Override
    public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
        // Setup cho partitions mới
        System.out.println("Partitions assigned: " + partitions);
    }
});
```

### Seek and Position

#### Seek to Specific Offset

```java
// Seek to beginning
consumer.seekToBeginning(consumer.assignment());

// Seek to end
consumer.seekToEnd(consumer.assignment());

// Seek to specific offset
TopicPartition partition = new TopicPartition("orders", 0);
consumer.seek(partition, 100);

// Seek by timestamp
long timestamp = Instant.now().minus(1, ChronoUnit.HOURS).toEpochMilli();
Map<TopicPartition, Long> timestampsToSearch = new HashMap<>();
for (TopicPartition partition : consumer.assignment()) {
    timestampsToSearch.put(partition, timestamp);
}
Map<TopicPartition, OffsetAndTimestamp> offsets =
    consumer.offsetsForTimes(timestampsToSearch);
```

### Consumer Best Practices

#### 1. Graceful Shutdown

```java
final KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);

Runtime.getRuntime().addShutdownHook(new Thread() {
    public void run() {
        consumer.wakeup();
    }
});

try {
    consumer.subscribe(Arrays.asList("orders"));

    while (true) {
        ConsumerRecords<String, String> records =
            consumer.poll(Duration.ofMillis(100));
        // Process records
    }
} catch (WakeupException e) {
    // Ignore, shutting down
} finally {
    consumer.close();
}
```

#### 2. Error Handling

```java
while (true) {
    try {
        ConsumerRecords<String, String> records =
            consumer.poll(Duration.ofMillis(100));

        for (ConsumerRecord<String, String> record : records) {
            try {
                processRecord(record);
            } catch (Exception e) {
                // Log error, send to DLQ, etc.
                handleProcessingError(record, e);
            }
        }

        consumer.commitSync();

    } catch (Exception e) {
        logger.error("Error in consumer loop", e);
    }
}
```

#### 3. Parallel Processing

```java
ExecutorService executor = Executors.newFixedThreadPool(10);

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

    List<Future<?>> futures = new ArrayList<>();

    for (ConsumerRecord<String, String> record : records) {
        Future<?> future = executor.submit(() -> processRecord(record));
        futures.add(future);
    }

    // Wait for all to complete
    for (Future<?> future : futures) {
        future.get();
    }

    consumer.commitSync();
}
```

#### 4. Monitor Consumer Lag

```java
Map<TopicPartition, Long> endOffsets = consumer.endOffsets(consumer.assignment());

for (TopicPartition partition : consumer.assignment()) {
    long currentPosition = consumer.position(partition);
    long endOffset = endOffsets.get(partition);
    long lag = endOffset - currentPosition;

    System.out.printf("Partition %d lag: %d%n", partition.partition(), lag);
}
```

## Performance Tuning

### Producer Performance

```properties
# Increase batch size
batch.size=65536
linger.ms=20

# Compression
compression.type=lz4

# Increase buffer memory
buffer.memory=67108864

# Max in-flight requests
max.in.flight.requests.per.connection=5
```

### Consumer Performance

```properties
# Fetch more data
fetch.min.bytes=1024
fetch.max.wait.ms=500

# Larger max poll
max.poll.records=1000

# Increase partition fetch size
max.partition.fetch.bytes=2097152
```

## Monitoring

### Producer Metrics
- `record-send-rate`
- `record-error-rate`
- `request-latency-avg`
- `buffer-available-bytes`

### Consumer Metrics
- `records-consumed-rate`
- `fetch-latency-avg`
- `records-lag-max`
- `commit-latency-avg`
