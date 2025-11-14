# Kafka Streams

## Tổng quan

**Kafka Streams** là thư viện Java/Scala để xử lý stream data trong Apache Kafka. Nó cho phép xây dựng ứng dụng xử lý real-time data một cách đơn giản và mạnh mẽ.

## Đặc điểm chính

### 1. Lightweight Library
- Không cần cluster riêng (không như Spark, Flink)
- Chạy như một Java application bình thường
- Deploy đơn giản

### 2. Exactly-Once Processing
- Đảm bảo mỗi record được xử lý đúng 1 lần
- Không duplicate, không mất data

### 3. Stateful Processing
- Hỗ trợ aggregations, joins, windowing
- State được lưu trữ cục bộ và backup vào Kafka

### 4. Fault Tolerance
- Tự động recovery khi failure
- State được replicate
- Rebalancing tự động

## Architecture

```
┌─────────────────────────────────────────┐
│    Kafka Streams Application            │
│  ┌───────────────────────────────────┐  │
│  │  Stream Processing Topology       │  │
│  │  ┌─────────────┐  ┌────────────┐ │  │
│  │  │   Source    │→ │ Processor  │ │  │
│  │  └─────────────┘  └─────┬──────┘ │  │
│  │                          ↓        │  │
│  │                   ┌────────────┐  │  │
│  │                   │    Sink    │  │  │
│  │                   └────────────┘  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │    State Stores (RocksDB)         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         ↕                      ↕
┌─────────────────┐    ┌─────────────────┐
│  Input Topics   │    │  Output Topics  │
└─────────────────┘    └─────────────────┘
```

## Core Concepts

### 1. Stream
Unbounded, continuously updating dataset.

```java
KStream<String, String> stream = builder.stream("input-topic");
```

### 2. Table
Changelog stream - mỗi key có 1 giá trị mới nhất.

```java
KTable<String, Long> table = builder.table("user-table");
```

### 3. GlobalKTable
Table được replicate toàn bộ trên mọi instance.

```java
GlobalKTable<String, String> globalTable =
    builder.globalTable("reference-data");
```

## Getting Started

### Dependencies

```xml
<dependency>
    <groupId>org.apache.kafka</groupId>
    <artifactId>kafka-streams</artifactId>
    <version>3.6.0</version>
</dependency>
```

### Basic Application

```java
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;

import java.util.Properties;

public class SimpleStreamsApp {
    public static void main(String[] args) {
        // Configuration
        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "simple-app");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG,
            Serdes.String().getClass());
        props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG,
            Serdes.String().getClass());

        // Build topology
        StreamsBuilder builder = new StreamsBuilder();
        KStream<String, String> source = builder.stream("input-topic");

        source.mapValues(value -> value.toUpperCase())
              .to("output-topic");

        // Start application
        KafkaStreams streams = new KafkaStreams(builder.build(), props);
        streams.start();

        // Graceful shutdown
        Runtime.getRuntime().addShutdownHook(new Thread(streams::close));
    }
}
```

## Stream Operations

### Stateless Operations

#### 1. Filter

```java
KStream<String, String> filtered = stream.filter(
    (key, value) -> value.length() > 10
);
```

#### 2. Map

```java
// mapValues - chỉ transform value
KStream<String, String> upper = stream.mapValues(
    value -> value.toUpperCase()
);

// map - transform cả key và value
KStream<String, Integer> mapped = stream.map(
    (key, value) -> KeyValue.pair(key.toUpperCase(), value.length())
);
```

#### 3. FlatMap

```java
KStream<String, String> words = stream.flatMapValues(
    value -> Arrays.asList(value.split("\\s+"))
);
```

#### 4. Branch

```java
KStream<String, String>[] branches = stream.branch(
    (key, value) -> value.startsWith("A"),
    (key, value) -> value.startsWith("B"),
    (key, value) -> true  // default
);
```

#### 5. Merge

```java
KStream<String, String> merged = stream1.merge(stream2);
```

### Stateful Operations

#### 1. Aggregation

```java
KTable<String, Long> wordCounts = words
    .groupBy((key, word) -> word)
    .count();
```

#### 2. Reduce

```java
KTable<String, String> reduced = stream
    .groupByKey()
    .reduce((aggValue, newValue) -> aggValue + "," + newValue);
```

#### 3. Join

**Stream-Stream Join:**
```java
KStream<String, String> joined = stream1.join(
    stream2,
    (leftValue, rightValue) -> leftValue + " - " + rightValue,
    JoinWindows.of(Duration.ofMinutes(5))
);
```

**Stream-Table Join:**
```java
KStream<String, String> enriched = userEvents.join(
    userTable,
    (event, userData) -> event + " by " + userData
);
```

**Table-Table Join:**
```java
KTable<String, String> joined = table1.join(
    table2,
    (value1, value2) -> value1 + " - " + value2
);
```

## Windowing

### Tumbling Window

```java
// Non-overlapping fixed-size windows
TimeWindowedKStream<String, String> windowed = stream
    .groupByKey()
    .windowedBy(TimeWindows.of(Duration.ofMinutes(5)));

KTable<Windowed<String>, Long> counts = windowed.count();
```

```
Timeline:
|----5min----|----5min----|----5min----|
   Window 1     Window 2     Window 3
```

### Hopping Window

```java
// Overlapping windows
TimeWindowedKStream<String, String> windowed = stream
    .groupByKey()
    .windowedBy(
        TimeWindows.of(Duration.ofMinutes(5))
                   .advanceBy(Duration.ofMinutes(1))
    );
```

```
Timeline:
|----5min----|
   |----5min----|
      |----5min----|
```

### Sliding Window

```java
// Window moves with each record
stream.groupByKey()
      .windowedBy(SlidingWindows.withTimeDifferenceAndGrace(
          Duration.ofMinutes(5),
          Duration.ofMinutes(1)
      ))
      .count();
```

### Session Window

```java
// Dynamic windows based on activity
SessionWindowedKStream<String, String> sessionized = stream
    .groupByKey()
    .windowedBy(SessionWindows.with(Duration.ofMinutes(5)));
```

```
Events:    •    •  •        •   •  •
Windows:   |-----|  |        |-----|
          Session1  Session2
```

## Advanced Features

### 1. Interactive Queries

```java
// Add state store
StoreBuilder<KeyValueStore<String, Long>> storeBuilder =
    Stores.keyValueStoreBuilder(
        Stores.persistentKeyValueStore("counts-store"),
        Serdes.String(),
        Serdes.Long()
    );

builder.addStateStore(storeBuilder);

// Query store
ReadOnlyKeyValueStore<String, Long> store =
    streams.store(
        StoreQueryParameters.fromNameAndType(
            "counts-store",
            QueryableStoreTypes.keyValueStore()
        )
    );

Long count = store.get("some-key");
```

### 2. Custom Processors

```java
class MyProcessor implements Processor<String, String, String, String> {
    private ProcessorContext<String, String> context;

    @Override
    public void init(ProcessorContext<String, String> context) {
        this.context = context;
    }

    @Override
    public void process(Record<String, String> record) {
        // Custom processing logic
        String newValue = record.value().toUpperCase();
        context.forward(record.withValue(newValue));
    }

    @Override
    public void close() {
        // Cleanup
    }
}

// Use in topology
builder.stream("input")
       .process(() -> new MyProcessor())
       .to("output");
```

### 3. Exactly-Once Semantics

```java
Properties props = new Properties();
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG,
    StreamsConfig.EXACTLY_ONCE_V2);
```

## Word Count Example

```java
public class WordCountApp {
    public static void main(String[] args) {
        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "wordcount-app");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG,
            Serdes.String().getClass());
        props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG,
            Serdes.String().getClass());

        StreamsBuilder builder = new StreamsBuilder();

        // 1. Read from input topic
        KStream<String, String> textLines = builder.stream("text-input");

        // 2. Split into words
        KStream<String, String> words = textLines
            .flatMapValues(value -> Arrays.asList(value.toLowerCase().split("\\W+")));

        // 3. Count occurrences
        KTable<String, Long> wordCounts = words
            .groupBy((key, word) -> word)
            .count(Materialized.as("counts-store"));

        // 4. Write to output topic
        wordCounts.toStream()
                  .to("word-count-output", Produced.with(Serdes.String(), Serdes.Long()));

        KafkaStreams streams = new KafkaStreams(builder.build(), props);
        streams.start();

        Runtime.getRuntime().addShutdownHook(new Thread(streams::close));
    }
}
```

## Testing

### Test Topology

```java
import org.apache.kafka.streams.TopologyTestDriver;
import org.apache.kafka.streams.test.TestRecord;

@Test
public void testWordCount() {
    StreamsBuilder builder = new StreamsBuilder();
    // Build topology...

    try (TopologyTestDriver testDriver = new TopologyTestDriver(
            builder.build(), props)) {

        TestInputTopic<String, String> inputTopic = testDriver.createInputTopic(
            "input", new StringSerializer(), new StringSerializer());

        TestOutputTopic<String, Long> outputTopic = testDriver.createOutputTopic(
            "output", new StringDeserializer(), new LongDeserializer());

        // Send test data
        inputTopic.pipeInput("key", "hello world");
        inputTopic.pipeInput("key", "hello kafka");

        // Verify output
        assertEquals(2L, outputTopic.readKeyValue().value);
    }
}
```

## Best Practices

### 1. Configuration

```properties
# Application ID - unique per application
application.id=my-streams-app

# Replication factor for state stores
replication.factor=3

# Number of threads
num.stream.threads=4

# State directory
state.dir=/var/lib/kafka-streams

# Commit interval
commit.interval.ms=1000
```

### 2. Error Handling

```java
props.put(StreamsConfig.DEFAULT_DESERIALIZATION_EXCEPTION_HANDLER_CLASS_CONFIG,
    LogAndContinueExceptionHandler.class);

props.put(StreamsConfig.DEFAULT_PRODUCTION_EXCEPTION_HANDLER_CLASS_CONFIG,
    AlwaysFailProductionExceptionHandler.class);
```

### 3. Monitoring

```java
streams.setStateListener((newState, oldState) -> {
    System.out.println("State changed from " + oldState + " to " + newState);
});

streams.setUncaughtExceptionHandler((thread, exception) -> {
    System.err.println("Uncaught exception: " + exception);
    return StreamsUncaughtExceptionHandler.StreamThreadExceptionResponse.SHUTDOWN_CLIENT;
});
```

### 4. Scaling

- Tăng `num.stream.threads`
- Tăng số partitions của input topics
- Deploy nhiều instances (mỗi instance xử lý subset của partitions)

### 5. State Store Management

```java
// Persistent store (RocksDB)
StoreBuilder<KeyValueStore<String, Long>> persistentStore =
    Stores.keyValueStoreBuilder(
        Stores.persistentKeyValueStore("my-store"),
        Serdes.String(),
        Serdes.Long()
    );

// In-memory store
StoreBuilder<KeyValueStore<String, Long>> memoryStore =
    Stores.keyValueStoreBuilder(
        Stores.inMemoryKeyValueStore("my-store"),
        Serdes.String(),
        Serdes.Long()
    );
```

## Performance Tuning

```properties
# Increase throughput
buffered.records.per.partition=1000
cache.max.bytes.buffering=10485760

# RocksDB tuning
rocksdb.config.setter=com.example.MyRocksDBConfigSetter

# Commit interval
commit.interval.ms=30000
```

## Common Use Cases

1. **Real-time Analytics**: Tính toán metrics real-time
2. **Data Enrichment**: Join events với reference data
3. **Anomaly Detection**: Phát hiện patterns bất thường
4. **Event-driven Microservices**: Xử lý events giữa services
5. **Materialized Views**: Tạo views từ event streams
