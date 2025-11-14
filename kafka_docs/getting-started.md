# Hướng dẫn bắt đầu với Apache Kafka

## Cài đặt

### Yêu cầu hệ thống

- **Java**: JDK 11 trở lên
- **Memory**: Tối thiểu 4GB RAM
- **Disk**: Đủ không gian cho log storage
- **OS**: Linux, macOS, hoặc Windows

### Download Kafka

```bash
# Download
wget https://downloads.apache.org/kafka/3.6.0/kafka_2.13-3.6.0.tgz

# Extract
tar -xzf kafka_2.13-3.6.0.tgz
cd kafka_2.13-3.6.0
```

### Cài đặt Java

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openjdk-11-jdk

# macOS (với Homebrew)
brew install openjdk@11

# Verify
java -version
```

## Quick Start

### 1. Start Kafka với KRaft (Không cần ZooKeeper)

#### Generate Cluster ID

```bash
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
echo $KAFKA_CLUSTER_ID
```

#### Format Storage Directory

```bash
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties
```

#### Start Kafka Server

```bash
bin/kafka-server-start.sh config/kraft/server.properties
```

### 2. Start Kafka với ZooKeeper (Legacy)

#### Start ZooKeeper

```bash
bin/zookeeper-server-start.sh config/zookeeper.properties
```

#### Start Kafka Broker

```bash
# Terminal mới
bin/kafka-server-start.sh config/server.properties
```

## Làm việc với Topics

### Tạo Topic

```bash
bin/kafka-topics.sh --create \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

### List Topics

```bash
bin/kafka-topics.sh --list \
  --bootstrap-server localhost:9092
```

### Describe Topic

```bash
bin/kafka-topics.sh --describe \
  --topic my-topic \
  --bootstrap-server localhost:9092
```

**Output:**
```
Topic: my-topic    PartitionCount: 3    ReplicationFactor: 1
    Topic: my-topic    Partition: 0    Leader: 0    Replicas: 0    Isr: 0
    Topic: my-topic    Partition: 1    Leader: 0    Replicas: 0    Isr: 0
    Topic: my-topic    Partition: 2    Leader: 0    Replicas: 0    Isr: 0
```

### Modify Topic

```bash
# Increase partitions
bin/kafka-topics.sh --alter \
  --topic my-topic \
  --partitions 5 \
  --bootstrap-server localhost:9092

# Change configuration
bin/kafka-configs.sh --alter \
  --entity-type topics \
  --entity-name my-topic \
  --add-config retention.ms=86400000 \
  --bootstrap-server localhost:9092
```

### Delete Topic

```bash
bin/kafka-topics.sh --delete \
  --topic my-topic \
  --bootstrap-server localhost:9092
```

## Producing Messages

### Console Producer

```bash
bin/kafka-console-producer.sh \
  --topic my-topic \
  --bootstrap-server localhost:9092
```

**Gửi messages:**
```
> Hello Kafka
> This is message 2
> Another message
```

### Producer với Key

```bash
bin/kafka-console-producer.sh \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --property "parse.key=true" \
  --property "key.separator=:"
```

**Gửi messages:**
```
> key1:value1
> key2:value2
> key1:value3
```

### Producer từ File

```bash
bin/kafka-console-producer.sh \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  < messages.txt
```

## Consuming Messages

### Console Consumer

```bash
bin/kafka-console-consumer.sh \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --from-beginning
```

### Consumer với Group

```bash
bin/kafka-console-consumer.sh \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --group my-group \
  --from-beginning
```

### Consumer hiển thị Key

```bash
bin/kafka-console-consumer.sh \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --property print.key=true \
  --property key.separator=":"
```

### Consumer với Offset cụ thể

```bash
bin/kafka-console-consumer.sh \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --partition 0 \
  --offset 10
```

## Consumer Groups

### List Groups

```bash
bin/kafka-consumer-groups.sh --list \
  --bootstrap-server localhost:9092
```

### Describe Group

```bash
bin/kafka-consumer-groups.sh --describe \
  --group my-group \
  --bootstrap-server localhost:9092
```

**Output:**
```
GROUP     TOPIC     PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
my-group  my-topic  0          100             120             20
my-group  my-topic  1          150             150             0
my-group  my-topic  2          200             210             10
```

### Reset Offsets

```bash
# To earliest
bin/kafka-consumer-groups.sh --reset-offsets \
  --group my-group \
  --topic my-topic \
  --to-earliest \
  --execute \
  --bootstrap-server localhost:9092

# To latest
bin/kafka-consumer-groups.sh --reset-offsets \
  --group my-group \
  --topic my-topic \
  --to-latest \
  --execute \
  --bootstrap-server localhost:9092

# By offset
bin/kafka-consumer-groups.sh --reset-offsets \
  --group my-group \
  --topic my-topic:0 \
  --to-offset 100 \
  --execute \
  --bootstrap-server localhost:9092
```

## Java Producer Example

### Maven Dependencies

```xml
<dependencies>
    <dependency>
        <groupId>org.apache.kafka</groupId>
        <artifactId>kafka-clients</artifactId>
        <version>3.6.0</version>
    </dependency>
    <dependency>
        <groupId>org.slf4j</groupId>
        <artifactId>slf4j-simple</artifactId>
        <version>2.0.9</version>
    </dependency>
</dependencies>
```

### Producer Code

```java
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.serialization.StringSerializer;

import java.util.Properties;

public class SimpleProducer {
    public static void main(String[] args) {
        // Configuration
        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,
                  StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,
                  StringSerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.RETRIES_CONFIG, 3);

        // Create producer
        try (Producer<String, String> producer = new KafkaProducer<>(props)) {

            // Send messages
            for (int i = 0; i < 10; i++) {
                ProducerRecord<String, String> record =
                    new ProducerRecord<>("my-topic",
                                       "key-" + i,
                                       "value-" + i);

                producer.send(record, (metadata, exception) -> {
                    if (exception != null) {
                        exception.printStackTrace();
                    } else {
                        System.out.printf("Sent record to partition %d with offset %d%n",
                                        metadata.partition(), metadata.offset());
                    }
                });
            }

            // Flush and close
            producer.flush();
            System.out.println("Messages sent successfully!");
        }
    }
}
```

## Java Consumer Example

```java
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.serialization.StringDeserializer;

import java.time.Duration;
import java.util.Arrays;
import java.util.Properties;

public class SimpleConsumer {
    public static void main(String[] args) {
        // Configuration
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "my-consumer-group");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,
                  StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
                  StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");

        // Create consumer
        try (Consumer<String, String> consumer = new KafkaConsumer<>(props)) {

            // Subscribe
            consumer.subscribe(Arrays.asList("my-topic"));

            // Poll loop
            while (true) {
                ConsumerRecords<String, String> records =
                    consumer.poll(Duration.ofMillis(100));

                for (ConsumerRecord<String, String> record : records) {
                    System.out.printf("Received: key=%s, value=%s, partition=%d, offset=%d%n",
                                    record.key(), record.value(),
                                    record.partition(), record.offset());
                }

                // Manual commit
                consumer.commitSync();
            }
        }
    }
}
```

## Docker Setup

### Docker Compose

**docker-compose.yml:**
```yaml
version: '3'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
```

**Start:**
```bash
docker-compose up -d
```

### KRaft Mode với Docker

```yaml
version: '3'
services:
  kafka:
    image: confluentinc/cp-kafka:latest
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
```

## Performance Testing

### Producer Performance Test

```bash
bin/kafka-producer-perf-test.sh \
  --topic test-topic \
  --num-records 1000000 \
  --record-size 1024 \
  --throughput -1 \
  --producer-props bootstrap.servers=localhost:9092
```

### Consumer Performance Test

```bash
bin/kafka-consumer-perf-test.sh \
  --topic test-topic \
  --messages 1000000 \
  --threads 1 \
  --bootstrap-server localhost:9092
```

## Common Issues và Solutions

### 1. Connection Refused

**Problem:** Producer/Consumer không connect được.

**Solution:**
- Kiểm tra broker đang chạy
- Verify `bootstrap.servers` configuration
- Check firewall/network settings

### 2. Topic Not Found

**Problem:** Topic không tồn tại.

**Solution:**
```bash
# Enable auto topic creation
auto.create.topics.enable=true

# Or create topic manually
bin/kafka-topics.sh --create --topic my-topic ...
```

### 3. Out of Memory

**Problem:** Kafka broker crash vì thiếu memory.

**Solution:**
```bash
# Increase heap size trong kafka-server-start.sh
export KAFKA_HEAP_OPTS="-Xmx4G -Xms4G"
```

### 4. Replication Error

**Problem:** Replication factor lớn hơn số brokers.

**Solution:**
```bash
# Giảm replication factor
--replication-factor 1
```

## Next Steps

1. **Học về Kafka Streams** - Stream processing
2. **Kafka Connect** - Integration với external systems
3. **Schema Registry** - Schema management
4. **Security** - Authentication và Authorization
5. **Monitoring** - JMX metrics, Prometheus
6. **Production Deployment** - Multi-broker cluster setup
