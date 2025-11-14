# Kiến trúc Apache Kafka

## Tổng quan kiến trúc

Apache Kafka được xây dựng theo kiến trúc phân tán với các thành phần chính hoạt động độc lập nhưng kết nối chặt chẽ với nhau.

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Producer 1 │      │  Producer 2 │      │  Producer 3 │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Kafka Cluster │
                    │  ┌──────────┐  │
                    │  │ Broker 1 │  │
                    │  ├──────────┤  │
                    │  │ Broker 2 │  │
                    │  ├──────────┤  │
                    │  │ Broker 3 │  │
                    │  └──────────┘  │
                    └───────┬────────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
│ Consumer 1  │      │ Consumer 2  │      │ Consumer 3  │
└─────────────┘      └─────────────┘      └─────────────┘
```

## Các thành phần chính

### 1. Kafka Broker

**Broker** là server cơ bản trong Kafka cluster:

- Mỗi broker là một Kafka server instance
- Lưu trữ và quản lý partitions
- Xử lý requests từ producers và consumers
- Tự động replicate dữ liệu giữa các broker
- Mỗi broker được định danh bằng một ID duy nhất

**Cluster** bao gồm nhiều brokers:
- Thường có từ 3-5+ brokers trong production
- Load balancing tự động giữa các brokers
- Tăng độ tin cậy và khả năng chịu lỗi

### 2. Topics và Partitions

**Topic** là danh mục logic để tổ chức messages:

```
Topic: user-events
├── Partition 0: [msg0, msg3, msg6, ...]
├── Partition 1: [msg1, msg4, msg7, ...]
└── Partition 2: [msg2, msg5, msg8, ...]
```

**Partition** là đơn vị phân phối và song song hóa:

- Mỗi topic chia thành nhiều partitions
- Partition là một chuỗi messages có thứ tự
- Messages trong partition có offset tăng dần
- Partitions phân bố trên nhiều brokers

**Đặc điểm Partitions:**
- Immutable: Messages không thể sửa sau khi ghi
- Ordered: Thứ tự được đảm bảo trong mỗi partition
- Distributed: Phân tán trên cluster
- Replicated: Sao lưu để đảm bảo an toàn dữ liệu

### 3. Replication

Kafka sử dụng replication để đảm bảo độ tin cậy:

```
Partition 0 của Topic A:
├── Leader (Broker 1)    ← Xử lý read/write
├── Replica 1 (Broker 2) ← Follower
└── Replica 2 (Broker 3) ← Follower
```

**Replication Factor:**
- Số lượng copies của mỗi partition
- Thường set là 3 trong production
- RF=3 có thể chịu được 2 broker failures

**Leader và Follower:**
- **Leader**: Xử lý tất cả read/write cho partition
- **Follower**: Replicates dữ liệu từ leader
- **ISR (In-Sync Replica)**: Replicas đồng bộ với leader

### 4. Producers

**Producer** gửi dữ liệu vào Kafka:

```java
// Ví dụ Producer
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("key.serializer", "StringSerializer");
props.put("value.serializer", "StringSerializer");

KafkaProducer<String, String> producer =
    new KafkaProducer<>(props);

ProducerRecord<String, String> record =
    new ProducerRecord<>("topic", "key", "value");

producer.send(record);
```

**Cơ chế gửi message:**
1. Producer chọn partition (round-robin hoặc dựa trên key)
2. Batch messages để tăng hiệu suất
3. Compress dữ liệu (optional)
4. Gửi đến leader của partition
5. Nhận acknowledgment

**Partition Strategy:**
- **Round-robin**: Phân phối đều messages
- **Key-based**: Messages cùng key → cùng partition
- **Custom partitioner**: Logic tùy chỉnh

### 5. Consumers và Consumer Groups

**Consumer** đọc dữ liệu từ Kafka:

```java
// Ví dụ Consumer
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("group.id", "my-group");
props.put("key.deserializer", "StringDeserializer");
props.put("value.deserializer", "StringDeserializer");

KafkaConsumer<String, String> consumer =
    new KafkaConsumer<>(props);

consumer.subscribe(Arrays.asList("topic"));

while (true) {
    ConsumerRecords<String, String> records =
        consumer.poll(Duration.ofMillis(100));
    for (ConsumerRecord<String, String> record : records) {
        process(record);
    }
}
```

**Consumer Group:**
```
Topic với 4 partitions:
Consumer Group A:
├── Consumer 1 → Partition 0, 1
└── Consumer 2 → Partition 2, 3

Consumer Group B:
├── Consumer 1 → Partition 0, 1, 2, 3
```

**Đặc điểm:**
- Mỗi partition chỉ được đọc bởi 1 consumer trong group
- Nhiều groups có thể đọc cùng topic
- Rebalancing tự động khi thêm/bớt consumers

### 6. ZooKeeper và KRaft

**ZooKeeper (Legacy mode):**
- Quản lý metadata của cluster
- Lưu trữ broker configuration
- Quản lý leader election
- Theo dõi consumer offsets (cũ)

**KRaft Mode (Mới - thay thế ZooKeeper):**
- Kafka Raft metadata mode
- Giảm độ phức tạp hệ thống
- Cải thiện khả năng mở rộng
- Metadata được quản lý trong chính Kafka

```
KRaft Architecture:
┌─────────────────────────────┐
│  Kafka Cluster (KRaft)      │
│  ┌───────────────────────┐  │
│  │ Controller Quorum     │  │
│  │  - Controller 1       │  │
│  │  - Controller 2       │  │
│  │  - Controller 3       │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │ Broker Nodes          │  │
│  │  - Broker 1           │  │
│  │  - Broker 2           │  │
│  │  - Broker 3           │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

## Luồng dữ liệu

### Write Path (Producer → Kafka)

1. Producer tạo message
2. Serialization (key và value)
3. Chọn partition
4. Batching và compression
5. Gửi đến leader broker
6. Leader ghi vào log
7. Followers replicate
8. Acknowledgment về producer

### Read Path (Kafka → Consumer)

1. Consumer poll messages
2. Broker đọc từ log file
3. Deserialization
4. Consumer xử lý message
5. Commit offset

## Log Structure

Kafka lưu trữ messages dưới dạng append-only log:

```
Partition Log:
/kafka-logs/topic-0/
├── 00000000000000000000.log  ← Segment 1
├── 00000000000000000100.log  ← Segment 2
├── 00000000000000000200.log  ← Segment 3
└── 00000000000000000300.log  ← Active segment
```

**Đặc điểm:**
- Messages được append vào cuối log
- Segments cũ có thể được xóa (retention policy)
- Sử dụng zero-copy để tăng hiệu suất
- Memory-mapped files

## Scalability

### Horizontal Scaling
- Thêm brokers vào cluster
- Tăng số lượng partitions
- Partitions tự động phân phối

### Performance Optimization
- Batch processing
- Compression (gzip, snappy, lz4, zstd)
- Zero-copy transfers
- Page cache utilization

## Fault Tolerance

### Broker Failure
1. Controller phát hiện broker down
2. Leader election cho các partitions bị ảnh hưởng
3. Replica từ ISR được promote thành leader
4. Clients tự động reconnect đến leader mới

### Network Partition
- ISR tracking đảm bảo data consistency
- Min ISR configuration
- Unclean leader election control

## Best Practices

1. **Replication Factor**: Tối thiểu 3 trong production
2. **Partitions**: Đủ để phân phối load, không quá nhiều
3. **Retention**: Cấu hình dựa trên nhu cầu lưu trữ
4. **Monitoring**: Theo dõi lag, throughput, errors
5. **Security**: Enable authentication và encryption
6. **Backup**: Regular snapshots và disaster recovery plan
