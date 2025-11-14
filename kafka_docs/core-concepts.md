# Các khái niệm cơ bản của Apache Kafka

## 1. Message (Record)

**Message** là đơn vị dữ liệu cơ bản trong Kafka.

### Cấu trúc của Message

```
┌─────────────────────────────────┐
│          Message                │
├─────────────────────────────────┤
│ Timestamp                       │
│ Offset                          │
│ Key (optional)                  │
│ Value                           │
│ Headers (optional)              │
└─────────────────────────────────┘
```

**Các thành phần:**

- **Timestamp**: Thời gian message được tạo hoặc append
- **Offset**: ID duy nhất của message trong partition
- **Key**: Định danh message (dùng cho partitioning)
- **Value**: Nội dung chính của message
- **Headers**: Metadata bổ sung (key-value pairs)

### Ví dụ Message

```json
{
  "timestamp": 1699876543210,
  "offset": 12345,
  "key": "user-123",
  "value": {
    "userId": "123",
    "action": "login",
    "timestamp": "2024-11-13T10:30:00Z"
  },
  "headers": {
    "source": "mobile-app",
    "version": "2.1.0"
  }
}
```

## 2. Topic

**Topic** là danh mục logic để phân loại và tổ chức messages.

### Đặc điểm của Topic

- Tên duy nhất trong cluster
- Multi-subscriber: nhiều consumers có thể đọc cùng topic
- Durable: Messages được lưu trữ theo retention policy
- Partitioned: Chia thành nhiều partitions để scale

### Naming Convention

```
# Good examples
user-events
payment-transactions
order-updates
system-logs

# Avoid
UserEvents (camelCase)
user_events (underscore - có thể conflict với internal topics)
```

### Topic Configuration

```bash
# Tạo topic
kafka-topics.sh --create \
  --topic user-events \
  --partitions 3 \
  --replication-factor 3 \
  --config retention.ms=86400000 \
  --config compression.type=snappy

# List topics
kafka-topics.sh --list

# Describe topic
kafka-topics.sh --describe --topic user-events
```

## 3. Partition

**Partition** là đơn vị phân tán và song song hóa trong Kafka.

### Vai trò của Partition

1. **Scalability**: Phân tán data và load
2. **Parallelism**: Nhiều consumers xử lý song song
3. **Ordering**: Đảm bảo thứ tự trong từng partition

### Partition Layout

```
Topic: orders (3 partitions)

Partition 0:  [offset 0] [offset 1] [offset 2] ... [offset N]
              order-101  order-104  order-107

Partition 1:  [offset 0] [offset 1] [offset 2] ... [offset M]
              order-102  order-105  order-108

Partition 2:  [offset 0] [offset 1] [offset 2] ... [offset P]
              order-103  order-106  order-109
```

### Partition Assignment

**Khi producer gửi message:**

1. **Với Key**: `hash(key) % num_partitions`
   ```java
   // Messages với cùng userId luôn vào cùng partition
   producer.send(new ProducerRecord<>("orders", userId, order));
   ```

2. **Không có Key**: Round-robin hoặc sticky partitioning
   ```java
   producer.send(new ProducerRecord<>("orders", order));
   ```

3. **Custom Partitioner**:
   ```java
   public class CustomPartitioner implements Partitioner {
       public int partition(String topic, Object key, byte[] keyBytes,
                          Object value, byte[] valueBytes,
                          Cluster cluster) {
           // Custom logic
           return customPartitionLogic(key);
       }
   }
   ```

### Số lượng Partitions

**Cân nhắc khi chọn số partitions:**

- **Throughput**: Nhiều partitions = throughput cao hơn
- **Parallelism**: Tối đa bằng số partitions
- **Overhead**: Quá nhiều partitions tăng overhead
- **Rebalancing**: Nhiều partitions = rebalancing lâu hơn

**Công thức tham khảo:**
```
Partitions = max(T/p, T/c)
Trong đó:
- T: Target throughput
- p: Producer throughput per partition
- c: Consumer throughput per partition
```

## 4. Offset

**Offset** là vị trí của message trong partition.

### Các loại Offset

```
Partition Log:
┌────────────────────────────────────────────┐
│ 0 │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │ 8 │ 9 │   │
└────────────────────────────────────────────┘
      ↑           ↑                       ↑
  Last Committed  Current               Log End
    Offset        Position                Offset
```

1. **Log Start Offset**: Offset đầu tiên còn lại (sau retention)
2. **Current Offset**: Vị trí consumer đang đọc
3. **Committed Offset**: Vị trí đã được commit
4. **Log End Offset**: Offset tiếp theo sẽ được ghi

### Offset Management

**Auto Commit (mặc định):**
```java
props.put("enable.auto.commit", "true");
props.put("auto.commit.interval.ms", "5000");
```

**Manual Commit:**
```java
props.put("enable.auto.commit", "false");

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(100);
    for (ConsumerRecord<String, String> record : records) {
        processRecord(record);
    }
    consumer.commitSync(); // Đồng bộ
    // hoặc
    consumer.commitAsync(); // Bất đồng bộ
}
```

## 5. Consumer Group

**Consumer Group** cho phép nhiều consumers cùng đọc một topic theo cách distributed.

### Cách hoạt động

```
Topic: events (4 partitions)

Consumer Group A:
├── Consumer 1 → Partition 0
├── Consumer 2 → Partition 1
├── Consumer 3 → Partition 2
└── Consumer 4 → Partition 3

Consumer Group B:
├── Consumer 1 → Partition 0, 1
└── Consumer 2 → Partition 2, 3
```

### Quy tắc

1. Mỗi partition chỉ được assign cho 1 consumer trong group
2. 1 consumer có thể xử lý nhiều partitions
3. Nếu consumers > partitions, một số consumers sẽ idle

### Rebalancing

**Khi nào xảy ra rebalancing:**
- Consumer mới join group
- Consumer rời khỏi group (crash hoặc shutdown)
- Topic thêm partitions
- Consumer không gửi heartbeat

**Rebalancing Strategies:**

1. **Range Assignor** (mặc định):
   ```
   Partitions 0,1,2,3,4,5 với 3 consumers:
   C1: 0, 1
   C2: 2, 3
   C3: 4, 5
   ```

2. **Round Robin Assignor**:
   ```
   C1: 0, 3
   C2: 1, 4
   C3: 2, 5
   ```

3. **Sticky Assignor**:
   - Giữ assignment cũ nếu có thể
   - Giảm thiểu chuyển động partitions

4. **Cooperative Sticky** (Incremental):
   - Chỉ revoke cần thiết
   - Giảm stop-the-world time

## 6. Broker

**Broker** là server trong Kafka cluster.

### Vai trò của Broker

- Lưu trữ partitions
- Xử lý produce và fetch requests
- Replication management
- Leader election

### Broker Configuration

```properties
# Server Basics
broker.id=0
listeners=PLAINTEXT://localhost:9092

# Log Basics
log.dirs=/var/lib/kafka/data

# Replication
default.replication.factor=3
min.insync.replicas=2

# Log Retention
log.retention.hours=168
log.segment.bytes=1073741824
```

## 7. Replication

**Replication** đảm bảo fault tolerance và high availability.

### Replication Factor

```
Topic: payments, RF=3

Partition 0:
├── Leader: Broker 1      ← Handle all R/W
├── Follower: Broker 2    ← Replicate from leader
└── Follower: Broker 3    ← Replicate from leader
```

### ISR (In-Sync Replicas)

**ISR** là tập hợp replicas đang sync với leader:

```
Partition 0:
├── Leader: Broker 1 (ISR)
├── Replica: Broker 2 (ISR) ← Caught up
├── Replica: Broker 3 (Out of ISR) ← Lagging
```

**Min ISR Configuration:**
```properties
min.insync.replicas=2
```
- Yêu cầu tối thiểu 2 replicas in-sync
- Write sẽ fail nếu ISR < min.insync.replicas

## 8. Retention

**Retention** xác định thời gian lưu trữ messages.

### Retention Policies

1. **Time-based**:
   ```properties
   log.retention.ms=604800000  # 7 days
   log.retention.hours=168     # 7 days
   ```

2. **Size-based**:
   ```properties
   log.retention.bytes=1073741824  # 1GB per partition
   ```

3. **Compaction**:
   ```properties
   log.cleanup.policy=compact
   ```
   - Giữ lại message mới nhất cho mỗi key
   - Dùng cho changelog, snapshots

### Retention Example

```
Time-based (7 days):
┌────────────────────────────────────┐
│ Day 1 │ Day 2 │ ... │ Day 7 │ Day 8│
└────────────────────────────────────┘
                        ↑
                   Deleted after 7 days

Compaction:
Before: [key1:v1, key2:v1, key1:v2, key2:v2, key1:v3]
After:  [key2:v2, key1:v3]  ← Keep latest for each key
```

## 9. Serialization

**Serialization** chuyển đổi objects thành bytes.

### Built-in Serializers

```java
// String
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");

// Integer
props.put("value.serializer", "org.apache.kafka.common.serialization.IntegerSerializer");

// Byte Array
props.put("value.serializer", "org.apache.kafka.common.serialization.ByteArraySerializer");
```

### Custom Serialization

```java
// JSON
props.put("value.serializer", "org.apache.kafka.common.serialization.JsonSerializer");

// Avro
props.put("value.serializer", "io.confluent.kafka.serializers.KafkaAvroSerializer");
props.put("schema.registry.url", "http://localhost:8081");

// Protobuf
props.put("value.serializer", "io.confluent.kafka.serializers.protobuf.KafkaProtobufSerializer");
```

## 10. Acknowledgments (acks)

**Acknowledgments** xác định độ tin cậy của write operations.

### Acks Levels

```java
// acks=0: Fire and forget
props.put("acks", "0");
// Fastest, có thể mất data

// acks=1: Leader acknowledged
props.put("acks", "1");
// Cân bằng giữa performance và durability

// acks=all: All ISR acknowledged
props.put("acks", "all");
// Safest, chậm nhất
```

### Trade-offs

```
acks=0:  [Producer] ──X──> [Broker]
         Fastest, lowest durability

acks=1:  [Producer] ←──✓── [Leader]
         Medium speed, medium durability

acks=all: [Producer] ←──✓── [Leader + ISR]
          Slowest, highest durability
```

## Best Practices

1. **Topic Design**: Một topic cho một loại event
2. **Partitioning**: Dùng keys có distribution tốt
3. **Retention**: Set dựa trên business needs
4. **Replication**: RF >= 3 trong production
5. **Consumer Groups**: Group ID duy nhất cho mỗi application
6. **Offset Management**: Manual commit cho critical data
7. **Monitoring**: Theo dõi lag, throughput, errors
